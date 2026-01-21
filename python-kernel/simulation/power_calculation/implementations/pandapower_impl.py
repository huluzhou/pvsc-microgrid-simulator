"""
pandapower 计算内核实现
"""

from typing import Dict, Any, List
from ..interface import PowerCalculationKernel


class PandapowerKernel(PowerCalculationKernel):
    """pandapower 计算内核实现"""
    
    def __init__(self):
        try:
            import pandapower as pp
            self.pp = pp
            self.net = None
        except ImportError:
            raise ImportError("pandapower is not installed. Please install it with: pip install pandapower")
    
    def calculate_power_flow(self, topology_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行潮流计算"""
        try:
            # 转换拓扑数据为 pandapower 格式
            self.net = self.convert_topology(topology_data)
            
            # 执行潮流计算
            self.pp.runpp(self.net)
            
            # 提取结果
            results = {
                "converged": self.net.converged,
                "devices": {}
            }
            
            # 提取各设备的结果
            if hasattr(self.net, 'res_bus'):
                results["devices"]["buses"] = self.net.res_bus.to_dict()
            if hasattr(self.net, 'res_line'):
                results["devices"]["lines"] = self.net.res_line.to_dict()
            if hasattr(self.net, 'res_trafo'):
                results["devices"]["transformers"] = self.net.res_trafo.to_dict()
            if hasattr(self.net, 'res_gen'):
                results["devices"]["generators"] = self.net.res_gen.to_dict()
            if hasattr(self.net, 'res_load'):
                results["devices"]["loads"] = self.net.res_load.to_dict()
            if hasattr(self.net, 'res_storage'):
                results["devices"]["storages"] = self.net.res_storage.to_dict()
            
            return results
        except Exception as e:
            return {
                "converged": False,
                "error": str(e)
            }
    
    def convert_topology(self, topology: Dict[str, Any]) -> Any:
        """将系统拓扑转换为 pandapower 格式"""
        import pandapower as pp
        
        # 创建空网络
        net = pp.create_empty_network()
        
        # 设备映射：device_id -> pandapower 索引
        bus_map: Dict[str, int] = {}
        device_map: Dict[str, Dict[str, int]] = {
            "lines": {},
            "transformers": {},
            "switches": {},
            "generators": {},
            "loads": {},
            "storages": {},
        }
        
        # 第一步：创建所有母线（Node）
        devices = topology.get("devices", [])
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices}
        else:
            devices_dict = devices
        
        for device_id, device in devices_dict.items():
            device_type = device.get("device_type", "")
            properties = device.get("properties", {})
            
            if device_type == "Node":
                # 创建母线
                vn_kv = properties.get("voltage_level", 0.4)
                if isinstance(vn_kv, str):
                    try:
                        vn_kv = float(vn_kv)
                    except:
                        vn_kv = 0.4
                
                bus_idx = pp.create_bus(
                    net,
                    vn_kv=vn_kv,
                    name=device.get("name", device_id)
                )
                bus_map[device_id] = bus_idx
        
        # 第二步：创建连接设备（需要源和目标母线）
        connections = topology.get("connections", [])
        if isinstance(connections, list):
            connections_list = connections
        else:
            connections_list = list(connections.values()) if isinstance(connections, dict) else []
        
        for conn in connections_list:
            from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
            to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
            
            if from_id not in bus_map or to_id not in bus_map:
                continue
            
            from_bus = bus_map[from_id]
            to_bus = bus_map[to_id]
            conn_type = conn.get("connection_type", "line") if isinstance(conn, dict) else getattr(conn, "connection_type", "line")
            
            # 获取连接对应的设备
            conn_device_id = None
            for dev_id, dev in devices_dict.items():
                if dev.get("device_type", "") in ["Line", "Transformer", "Switch"]:
                    # 检查设备是否匹配此连接
                    conn_device_id = dev_id
                    break
            
            if conn_device_id and conn_device_id in devices_dict:
                device = devices_dict[conn_device_id]
                device_type = device.get("device_type", "")
                properties = device.get("properties", {})
                
                if device_type == "Line":
                    # 创建线路
                    length_km = properties.get("length", 1.0)
                    if isinstance(length_km, str):
                        try:
                            length_km = float(length_km)
                        except:
                            length_km = 1.0
                    
                    std_type = properties.get("cable_type", "NAYY 4x50 SE")
                    line_idx = pp.create_line(
                        net,
                        from_bus=from_bus,
                        to_bus=to_bus,
                        length_km=length_km,
                        std_type=std_type,
                        name=device.get("name", conn_device_id)
                    )
                    device_map["lines"][conn_device_id] = line_idx
                
                elif device_type == "Transformer":
                    # 创建变压器
                    sn_mva = properties.get("rated_power", 0.63)
                    if isinstance(sn_mva, str):
                        try:
                            sn_mva = float(sn_mva) / 1000.0  # 转换为 MVA
                        except:
                            sn_mva = 0.63
                    
                    vn_hv_kv = properties.get("high_voltage", 20.0)
                    vn_lv_kv = properties.get("low_voltage", 0.4)
                    if isinstance(vn_hv_kv, str):
                        try:
                            vn_hv_kv = float(vn_hv_kv)
                        except:
                            vn_hv_kv = 20.0
                    if isinstance(vn_lv_kv, str):
                        try:
                            vn_lv_kv = float(vn_lv_kv)
                        except:
                            vn_lv_kv = 0.4
                    
                    trafo_idx = pp.create_transformer(
                        net,
                        hv_bus=from_bus,
                        lv_bus=to_bus,
                        std_type="0.25 MVA 20/0.4 kV",
                        name=device.get("name", conn_device_id)
                    )
                    device_map["transformers"][conn_device_id] = trafo_idx
                
                elif device_type == "Switch":
                    # 创建开关
                    switch_idx = pp.create_switch(
                        net,
                        bus=from_bus,
                        element=to_bus,
                        et="b",  # bus-bus switch
                        closed=properties.get("is_closed", True),
                        name=device.get("name", conn_device_id)
                    )
                    device_map["switches"][conn_device_id] = switch_idx
        
        # 第三步：创建功率设备（需要连接到母线）
        for device_id, device in devices_dict.items():
            device_type = device.get("device_type", "")
            properties = device.get("properties", {})
            
            # 找到设备连接的母线
            connected_bus = None
            for conn in connections_list:
                from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
                to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
                
                if device_id == to_id and from_id in bus_map:
                    connected_bus = bus_map[from_id]
                    break
                elif device_id == from_id and to_id in bus_map:
                    connected_bus = bus_map[to_id]
                    break
            
            if connected_bus is None:
                # 如果没有找到连接，创建默认母线
                vn_kv = properties.get("voltage_level", 0.4)
                if isinstance(vn_kv, str):
                    try:
                        vn_kv = float(vn_kv)
                    except:
                        vn_kv = 0.4
                connected_bus = pp.create_bus(net, vn_kv=vn_kv, name=f"{device_id}_bus")
                bus_map[device_id] = connected_bus
            
            if device_type == "Pv":
                # 创建光伏发电机
                p_mw = properties.get("rated_power", 0.0)
                if isinstance(p_mw, str):
                    try:
                        p_mw = float(p_mw) / 1000.0  # 转换为 MW
                    except:
                        p_mw = 0.0
                
                gen_idx = pp.create_gen(
                    net,
                    bus=connected_bus,
                    p_mw=p_mw,
                    vm_pu=1.0,
                    name=device.get("name", device_id)
                )
                device_map["generators"][device_id] = gen_idx
            
            elif device_type == "Load":
                # 创建负载
                p_mw = properties.get("rated_power", 0.0)
                if isinstance(p_mw, str):
                    try:
                        p_mw = float(p_mw) / 1000.0  # 转换为 MW
                    except:
                        p_mw = 0.0
                
                load_idx = pp.create_load(
                    net,
                    bus=connected_bus,
                    p_mw=p_mw,
                    q_mvar=0.0,
                    name=device.get("name", device_id)
                )
                device_map["loads"][device_id] = load_idx
            
            elif device_type == "Storage":
                # 创建储能设备
                p_mw = properties.get("rated_power", 0.0)
                if isinstance(p_mw, str):
                    try:
                        p_mw = float(p_mw) / 1000.0  # 转换为 MW
                    except:
                        p_mw = 0.0
                
                max_e_mwh = properties.get("capacity", 0.0)
                if isinstance(max_e_mwh, str):
                    try:
                        max_e_mwh = float(max_e_mwh) / 1000.0  # 转换为 MWh
                    except:
                        max_e_mwh = 0.0
                
                storage_idx = pp.create_storage(
                    net,
                    bus=connected_bus,
                    p_mw=p_mw,
                    max_e_mwh=max_e_mwh,
                    name=device.get("name", device_id)
                )
                device_map["storages"][device_id] = storage_idx
            
            elif device_type == "Charger":
                # 充电桩作为负载处理
                p_mw = properties.get("rated_power", 0.0)
                if isinstance(p_mw, str):
                    try:
                        p_mw = float(p_mw) / 1000.0  # 转换为 MW
                    except:
                        p_mw = 0.0
                
                load_idx = pp.create_load(
                    net,
                    bus=connected_bus,
                    p_mw=p_mw,
                    q_mvar=0.0,
                    name=device.get("name", device_id)
                )
                device_map["loads"][device_id] = load_idx
        
        return net
    
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        return [
            "AC power flow",
            "DC power flow",
            "OPF (Optimal Power Flow)",
            "Short circuit calculation"
        ]
