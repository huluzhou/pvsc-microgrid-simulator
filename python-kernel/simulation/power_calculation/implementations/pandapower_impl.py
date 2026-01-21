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
        
        # 转换设备
        devices = topology.get("devices", {})
        for device_id, device in devices.items():
            device_type = device.get("device_type", "")
            
            if device_type == "Node":
                # 创建母线
                pp.create_bus(
                    net,
                    vn_kv=device.get("properties", {}).get("voltage_level", 0.4),
                    name=device.get("name", device_id)
                )
            elif device_type == "Line":
                # 创建线路（需要源和目标母线）
                # 这里简化处理，实际需要根据连接关系
                pass
            elif device_type == "Transformer":
                # 创建变压器
                pass
            # 其他设备类型...
        
        return net
    
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        return [
            "AC power flow",
            "DC power flow",
            "OPF (Optimal Power Flow)",
            "Short circuit calculation"
        ]
