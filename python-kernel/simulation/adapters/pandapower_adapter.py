"""
Pandapower 拓扑数据适配器
将标准拓扑数据格式转换为 pandapower 网络格式
"""

from typing import Dict, Any, List, Optional
from .topology_adapter import TopologyAdapter, AdapterResult, AdapterError
import warnings


class PandapowerTopologyAdapter(TopologyAdapter):
    """Pandapower 拓扑数据适配器"""
    
    def __init__(self):
        try:
            import pandapower as pp
            self.pp = pp
        except ImportError:
            raise ImportError("pandapower is not installed. Please install it with: pip install pandapower")
        
        # 保存映射信息，供后续更新功率值使用
        self.bus_map: Dict[str, int] = {}
        self.device_map: Dict[str, Dict[str, int]] = {
            "lines": {},
            "transformers": {},
            "switches": {},
            "generators": {},
            "loads": {},
            "storages": {},
        }
    
    def get_bus_map(self) -> Dict[str, int]:
        """获取设备ID到母线索引的映射"""
        return self.bus_map.copy()
    
    def get_device_map(self) -> Dict[str, Dict[str, int]]:
        """获取设备ID到pandapower元素索引的映射"""
        return {k: v.copy() for k, v in self.device_map.items()}
    
    def convert(self, topology_data: Dict[str, Any]) -> AdapterResult:
        """
        将标准拓扑数据格式转换为 pandapower 网络格式
        
        Args:
            topology_data: 标准拓扑数据格式
        
        Returns:
            AdapterResult: 包含转换结果、错误和警告
        """
        errors: List[AdapterError] = []
        warnings_list: List[AdapterError] = []
        
        try:
            # 验证拓扑数据
            validation_errors = self.validate(topology_data)
            errors.extend([e for e in validation_errors if e.severity == "error"])
            warnings_list.extend([e for e in validation_errors if e.severity == "warning"])
            
            # 创建空网络
            net = self.pp.create_empty_network()
            
            # 设备映射：device_id -> pandapower 索引
            # 使用实例变量保存映射信息，供后续更新功率值使用
            self.bus_map.clear()
            for key in self.device_map:
                self.device_map[key].clear()
            
            bus_map = self.bus_map
            device_map = self.device_map
            
            # 获取设备字典
            devices = topology_data.get("devices", {})
            if isinstance(devices, list):
                devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
            else:
                devices_dict = devices
            
            # 第一步：创建所有母线（Node）
            for device_id, device in devices_dict.items():
                device_type = device.get("device_type", "")
                
                if device_type == "Node":
                    try:
                        bus_idx = self._create_bus(net, device_id, device, bus_map, errors, warnings_list)
                        if bus_idx is not None:
                            bus_map[device_id] = bus_idx
                    except Exception as e:
                        errors.append(AdapterError(
                            error_type="topology",
                            severity="error",
                            message=f"创建母线失败: {str(e)}",
                            device_id=device_id,
                            details={"device": device}
                        ))
            
            # 获取连接列表
            connections = topology_data.get("connections", [])
            if isinstance(connections, list):
                connections_list = connections
            else:
                connections_list = list(connections.values()) if isinstance(connections, dict) else []
            
            # 第二步：创建连接设备（Line, Transformer, Switch）
            for conn in connections_list:
                try:
                    self._create_connection_device(
                        net, conn, devices_dict, bus_map, device_map,
                        connections_list, errors, warnings_list
                    )
                except Exception as e:
                    conn_id = conn.get("id", "unknown") if isinstance(conn, dict) else getattr(conn, "id", "unknown")
                    errors.append(AdapterError(
                        error_type="topology",
                        severity="error",
                        message=f"创建连接设备失败: {str(e)}",
                        device_id=conn_id,
                        details={"connection": conn}
                    ))
            
            # 第三步：创建功率设备（Pv, Load, Storage, Charger, ExternalGrid）
            for device_id, device in devices_dict.items():
                device_type = device.get("device_type", "")
                
                if device_type in ["Pv", "Load", "Storage", "Charger", "ExternalGrid"]:
                    try:
                        self._create_power_device(
                            net, device_id, device, devices_dict, connections_list,
                            bus_map, device_map, errors, warnings_list
                        )
                    except Exception as e:
                        errors.append(AdapterError(
                            error_type="topology",
                            severity="error",
                            message=f"创建功率设备失败: {str(e)}",
                            device_id=device_id,
                            details={"device": device}
                        ))
            
            # 检查是否有外部电网
            external_grids = [d for d in devices_dict.values() if d.get("device_type") == "ExternalGrid"]
            if not external_grids:
                warnings_list.append(AdapterError(
                    error_type="topology",
                    severity="warning",
                    message="未找到外部电网，网络可能无法计算",
                    details={}
                ))
            
            success = len(errors) == 0 or all(e.severity != "error" for e in errors)
            
            return AdapterResult(
                success=success,
                data=net,
                errors=errors,
                warnings=warnings_list
            )
            
        except Exception as e:
            errors.append(AdapterError(
                error_type="adapter",
                severity="error",
                message=f"适配器转换失败: {str(e)}",
                details={"exception": str(e), "type": type(e).__name__}
            ))
            return AdapterResult(
                success=False,
                data=None,
                errors=errors,
                warnings=warnings_list
            )
    
    def _create_bus(self, net, device_id: str, device: Dict[str, Any],
                    bus_map: Dict[str, int], errors: List[AdapterError],
                    warnings: List[AdapterError]) -> Optional[int]:
        """创建母线"""
        properties = device.get("properties", {})
        
        # 获取电压等级
        vn_kv = properties.get("voltage_level")
        if vn_kv is None:
            vn_kv = self.get_default_value("Node", "voltage_level")
            warnings.append(AdapterError(
                error_type="adapter",
                severity="warning",
                message=f"设备 {device_id} 缺少电压等级，使用默认值 {vn_kv} kV",
                device_id=device_id
            ))
        
        # 类型转换
        if isinstance(vn_kv, str):
            try:
                vn_kv = float(vn_kv)
            except ValueError:
                vn_kv = self.get_default_value("Node", "voltage_level")
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"设备 {device_id} 电压等级格式错误，使用默认值 {vn_kv} kV",
                    device_id=device_id
                ))
        
        if vn_kv <= 0:
            errors.append(AdapterError(
                error_type="adapter",
                severity="error",
                message=f"设备 {device_id} 电压等级无效: {vn_kv}",
                device_id=device_id
            ))
            return None
        
        try:
            bus_idx = self.pp.create_bus(
                net,
                vn_kv=vn_kv,
                name=device.get("name", device_id)
            )
            return bus_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建母线失败: {str(e)}",
                device_id=device_id,
                details={"vn_kv": vn_kv}
            ))
            return None
    
    def _create_connection_device(self, net, conn: Dict[str, Any],
                                  devices_dict: Dict[str, Dict[str, Any]],
                                  bus_map: Dict[str, int],
                                  device_map: Dict[str, Dict[str, int]],
                                  connections_list: List[Dict[str, Any]],
                                  errors: List[AdapterError],
                                  warnings: List[AdapterError]):
        """创建连接设备（Line, Transformer, Switch）"""
        from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
        to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
        
        # 检查母线是否存在
        if from_id not in bus_map:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"连接源设备 {from_id} 不是有效的母线",
                details={"connection": conn}
            ))
            return
        
        if to_id not in bus_map:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"连接目标设备 {to_id} 不是有效的母线",
                details={"connection": conn}
            ))
            return
        
        from_bus = bus_map[from_id]
        to_bus = bus_map[to_id]
        
        # 查找连接对应的设备
        conn_device_id = None
        conn_type = conn.get("connection_type", "line") if isinstance(conn, dict) else getattr(conn, "connection_type", "line")
        
        # 根据连接类型查找设备
        for dev_id, dev in devices_dict.items():
            dev_type = dev.get("device_type", "")
            if conn_type == "line" and dev_type == "Line":
                # 检查设备是否连接这两个母线
                if self._device_connects_buses(dev_id, from_id, to_id, connections_list):
                    conn_device_id = dev_id
                    break
            elif conn_type == "transformer" and dev_type == "Transformer":
                if self._device_connects_buses(dev_id, from_id, to_id, connections_list):
                    conn_device_id = dev_id
                    break
            elif conn_type == "switch" and dev_type == "Switch":
                if self._device_connects_buses(dev_id, from_id, to_id, connections_list):
                    conn_device_id = dev_id
                    break
        
        if not conn_device_id:
            # 如果没有找到对应设备，根据连接类型创建
            if conn_type == "line":
                self._create_line_direct(net, from_bus, to_bus, conn, errors, warnings)
            return
        
        device = devices_dict.get(conn_device_id)
        if not device:
            return
        
        device_type = device.get("device_type", "")
        properties = device.get("properties", {})
        
        if device_type == "Line":
            self._create_line(net, conn_device_id, device, from_bus, to_bus, device_map, errors, warnings)
        elif device_type == "Transformer":
            self._create_transformer(net, conn_device_id, device, from_bus, to_bus, device_map, errors, warnings)
        elif device_type == "Switch":
            self._create_switch(net, conn_device_id, device, from_bus, to_bus, device_map, errors, warnings)
    
    def _device_connects_buses(self, device_id: str, bus1_id: str, bus2_id: str,
                              connections_list: List[Dict[str, Any]]) -> bool:
        """检查设备是否连接两个母线"""
        for conn in connections_list:
            from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
            to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
            
            # 检查设备是否在连接中
            if (from_id == device_id and to_id in [bus1_id, bus2_id]) or \
               (to_id == device_id and from_id in [bus1_id, bus2_id]):
                # 检查另一个端点
                other_id = bus2_id if from_id == bus1_id or to_id == bus1_id else bus1_id
                if (from_id == other_id or to_id == other_id):
                    return True
        return False
    
    def _create_line(self, net, device_id: str, device: Dict[str, Any],
                    from_bus: int, to_bus: int,
                    device_map: Dict[str, Dict[str, int]],
                    errors: List[AdapterError], warnings: List[AdapterError]):
        """创建线路"""
        properties = device.get("properties", {})
        
        length_km = properties.get("length")
        if length_km is None:
            length_km = self.get_default_value("Line", "length")
            warnings.append(AdapterError(
                error_type="adapter",
                severity="warning",
                message=f"线路 {device_id} 缺少长度，使用默认值 {length_km} km",
                device_id=device_id
            ))
        
        if isinstance(length_km, str):
            try:
                length_km = float(length_km)
            except ValueError:
                length_km = self.get_default_value("Line", "length")
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"线路 {device_id} 长度格式错误，使用默认值 {length_km} km",
                    device_id=device_id
                ))
        
        std_type = properties.get("cable_type", self.get_default_value("Line", "cable_type"))
        
        try:
            line_idx = self.pp.create_line(
                net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=length_km,
                std_type=std_type,
                name=device.get("name", device_id)
            )
            device_map["lines"][device_id] = line_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建线路失败: {str(e)}",
                device_id=device_id,
                details={"length_km": length_km, "std_type": std_type}
            ))
    
    def _create_line_direct(self, net, from_bus: int, to_bus: int,
                           conn: Dict[str, Any], errors: List[AdapterError],
                           warnings: List[AdapterError]):
        """直接创建线路（没有对应设备时）"""
        try:
            line_idx = self.pp.create_line(
                net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=1.0,
                std_type="NAYY 4x50 SE",
                name=f"line_{from_bus}_{to_bus}"
            )
            warnings.append(AdapterError(
                error_type="adapter",
                severity="warning",
                message=f"连接 {conn.get('id', 'unknown')} 没有对应设备，创建默认线路",
                details={"connection": conn}
            ))
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建默认线路失败: {str(e)}",
                details={"connection": conn}
            ))
    
    def _create_transformer(self, net, device_id: str, device: Dict[str, Any],
                           from_bus: int, to_bus: int,
                           device_map: Dict[str, Dict[str, int]],
                           errors: List[AdapterError], warnings: List[AdapterError]):
        """创建变压器"""
        properties = device.get("properties", {})
        
        # 获取额定功率（kW -> MVA）
        rated_power = properties.get("rated_power")
        if rated_power is None:
            rated_power = self.get_default_value("Transformer", "rated_power") * 1000  # MVA -> kW
            warnings.append(AdapterError(
                error_type="adapter",
                severity="warning",
                message=f"变压器 {device_id} 缺少额定功率，使用默认值",
                device_id=device_id
            ))
        
        if isinstance(rated_power, str):
            try:
                rated_power = float(rated_power)
            except ValueError:
                rated_power = self.get_default_value("Transformer", "rated_power") * 1000
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"变压器 {device_id} 额定功率格式错误，使用默认值",
                    device_id=device_id
                ))
        
        sn_mva = rated_power / 1000.0  # kW -> MVA
        
        # 获取电压等级
        vn_hv_kv = properties.get("high_voltage", self.get_default_value("Transformer", "high_voltage"))
        vn_lv_kv = properties.get("low_voltage", self.get_default_value("Transformer", "low_voltage"))
        
        if isinstance(vn_hv_kv, str):
            try:
                vn_hv_kv = float(vn_hv_kv)
            except ValueError:
                vn_hv_kv = self.get_default_value("Transformer", "high_voltage")
        
        if isinstance(vn_lv_kv, str):
            try:
                vn_lv_kv = float(vn_lv_kv)
            except ValueError:
                vn_lv_kv = self.get_default_value("Transformer", "low_voltage")
        
        # 使用标准类型
        std_type = f"{sn_mva} MVA {vn_hv_kv}/{vn_lv_kv} kV"
        
        try:
            trafo_idx = self.pp.create_transformer(
                net,
                hv_bus=from_bus,
                lv_bus=to_bus,
                std_type=std_type,
                name=device.get("name", device_id)
            )
            device_map["transformers"][device_id] = trafo_idx
        except Exception as e:
            # 如果标准类型不存在，尝试使用默认类型
            try:
                trafo_idx = self.pp.create_transformer(
                    net,
                    hv_bus=from_bus,
                    lv_bus=to_bus,
                    std_type="0.25 MVA 20/0.4 kV",
                    name=device.get("name", device_id)
                )
                device_map["transformers"][device_id] = trafo_idx
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"变压器 {device_id} 使用默认标准类型",
                    device_id=device_id
                ))
            except Exception as e2:
                errors.append(AdapterError(
                    error_type="topology",
                    severity="error",
                    message=f"创建变压器失败: {str(e2)}",
                    device_id=device_id,
                    details={"sn_mva": sn_mva, "vn_hv_kv": vn_hv_kv, "vn_lv_kv": vn_lv_kv}
                ))
    
    def _create_switch(self, net, device_id: str, device: Dict[str, Any],
                     from_bus: int, to_bus: int,
                     device_map: Dict[str, Dict[str, int]],
                     errors: List[AdapterError], warnings: List[AdapterError]):
        """创建开关"""
        properties = device.get("properties", {})
        is_closed = properties.get("is_closed", True)
        
        try:
            switch_idx = self.pp.create_switch(
                net,
                bus=from_bus,
                element=to_bus,
                et="b",  # bus-bus switch
                closed=bool(is_closed),
                name=device.get("name", device_id)
            )
            device_map["switches"][device_id] = switch_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建开关失败: {str(e)}",
                device_id=device_id
            ))
    
    def _create_power_device(self, net, device_id: str, device: Dict[str, Any],
                            devices_dict: Dict[str, Dict[str, Any]],
                            connections_list: List[Dict[str, Any]],
                            bus_map: Dict[str, int],
                            device_map: Dict[str, Dict[str, int]],
                            errors: List[AdapterError], warnings: List[AdapterError]):
        """创建功率设备"""
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
        
        # 如果没有找到连接，创建默认母线
        if connected_bus is None:
            vn_kv = properties.get("voltage_level")
            if vn_kv is None:
                if device_type == "ExternalGrid":
                    vn_kv = self.get_default_value("ExternalGrid", "voltage_level")
                else:
                    vn_kv = self.get_default_value("Node", "voltage_level")
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"设备 {device_id} 未连接到母线，创建默认母线",
                    device_id=device_id
                ))
            
            if isinstance(vn_kv, str):
                try:
                    vn_kv = float(vn_kv)
                except ValueError:
                    vn_kv = 0.4
            
            try:
                connected_bus = self.pp.create_bus(net, vn_kv=vn_kv, name=f"{device_id}_bus")
                bus_map[device_id] = connected_bus
            except Exception as e:
                errors.append(AdapterError(
                    error_type="topology",
                    severity="error",
                    message=f"为设备 {device_id} 创建默认母线失败: {str(e)}",
                    device_id=device_id
                ))
                return
        
        # 根据设备类型创建
        if device_type == "Pv":
            self._create_generator(net, device_id, device, connected_bus, device_map, errors, warnings)
        elif device_type == "Load" or device_type == "Charger":
            self._create_load(net, device_id, device, connected_bus, device_map, errors, warnings)
        elif device_type == "Storage":
            self._create_storage(net, device_id, device, connected_bus, device_map, errors, warnings)
        elif device_type == "ExternalGrid":
            self._create_external_grid(net, device_id, device, connected_bus, errors, warnings)
    
    def _create_generator(self, net, device_id: str, device: Dict[str, Any],
                         bus: int, device_map: Dict[str, Dict[str, int]],
                         errors: List[AdapterError], warnings: List[AdapterError]):
        """创建发电机（光伏）"""
        properties = device.get("properties", {})
        
        p_mw = properties.get("rated_power", 0.0)
        if isinstance(p_mw, str):
            try:
                p_mw = float(p_mw) / 1000.0  # kW -> MW
            except ValueError:
                p_mw = 0.0
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"发电机 {device_id} 功率格式错误，使用默认值 0",
                    device_id=device_id
                ))
        else:
            p_mw = float(p_mw) / 1000.0 if p_mw else 0.0
        
        try:
            gen_idx = self.pp.create_gen(
                net,
                bus=bus,
                p_mw=p_mw,
                vm_pu=1.0,
                name=device.get("name", device_id)
            )
            device_map["generators"][device_id] = gen_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建发电机失败: {str(e)}",
                device_id=device_id,
                details={"p_mw": p_mw}
            ))
    
    def _create_load(self, net, device_id: str, device: Dict[str, Any],
                    bus: int, device_map: Dict[str, Dict[str, int]],
                    errors: List[AdapterError], warnings: List[AdapterError]):
        """创建负载"""
        properties = device.get("properties", {})
        
        p_mw = properties.get("rated_power", 0.0)
        if isinstance(p_mw, str):
            try:
                p_mw = float(p_mw) / 1000.0  # kW -> MW
            except ValueError:
                p_mw = 0.0
                warnings.append(AdapterError(
                    error_type="adapter",
                    severity="warning",
                    message=f"负载 {device_id} 功率格式错误，使用默认值 0",
                    device_id=device_id
                ))
        else:
            p_mw = float(p_mw) / 1000.0 if p_mw else 0.0
        
        try:
            load_idx = self.pp.create_load(
                net,
                bus=bus,
                p_mw=p_mw,
                q_mvar=0.0,
                name=device.get("name", device_id)
            )
            device_map["loads"][device_id] = load_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建负载失败: {str(e)}",
                device_id=device_id,
                details={"p_mw": p_mw}
            ))
    
    def _create_storage(self, net, device_id: str, device: Dict[str, Any],
                       bus: int, device_map: Dict[str, Dict[str, int]],
                       errors: List[AdapterError], warnings: List[AdapterError]):
        """创建储能设备"""
        properties = device.get("properties", {})
        
        p_mw = properties.get("rated_power", 0.0)
        if isinstance(p_mw, str):
            try:
                p_mw = float(p_mw) / 1000.0  # kW -> MW
            except ValueError:
                p_mw = 0.0
        else:
            p_mw = float(p_mw) / 1000.0 if p_mw else 0.0
        
        max_e_mwh = properties.get("capacity", 0.0)
        if isinstance(max_e_mwh, str):
            try:
                max_e_mwh = float(max_e_mwh) / 1000.0  # kWh -> MWh
            except ValueError:
                max_e_mwh = 0.0
        else:
            max_e_mwh = float(max_e_mwh) / 1000.0 if max_e_mwh else 0.0
        
        try:
            storage_idx = self.pp.create_storage(
                net,
                bus=bus,
                p_mw=p_mw,
                max_e_mwh=max_e_mwh,
                name=device.get("name", device_id)
            )
            device_map["storages"][device_id] = storage_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建储能设备失败: {str(e)}",
                device_id=device_id,
                details={"p_mw": p_mw, "max_e_mwh": max_e_mwh}
            ))
    
    def _create_external_grid(self, net, device_id: str, device: Dict[str, Any],
                             bus: int, errors: List[AdapterError], warnings: List[AdapterError]):
        """创建外部电网"""
        properties = device.get("properties", {})
        
        vn_kv = properties.get("voltage_level", 10.0)
        if isinstance(vn_kv, str):
            try:
                vn_kv = float(vn_kv)
            except ValueError:
                vn_kv = 10.0
        
        try:
            self.pp.create_ext_grid(
                net,
                bus=bus,
                vm_pu=1.0,
                name=device.get("name", device_id)
            )
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建外部电网失败: {str(e)}",
                device_id=device_id
            ))
    
    def validate(self, topology_data: Dict[str, Any]) -> List[AdapterError]:
        """
        验证拓扑数据的完整性和有效性
        
        Args:
            topology_data: 标准拓扑数据格式
        
        Returns:
            List[AdapterError]: 验证错误列表
        """
        errors: List[AdapterError] = []
        
        # 检查基本结构
        if "devices" not in topology_data:
            errors.append(AdapterError(
                error_type="validation",
                severity="error",
                message="拓扑数据缺少 'devices' 字段",
                details={}
            ))
            return errors
        
        if "connections" not in topology_data:
            errors.append(AdapterError(
                error_type="validation",
                severity="warning",
                message="拓扑数据缺少 'connections' 字段",
                details={}
            ))
        
        devices = topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        
        # 检查设备
        node_count = 0
        for device_id, device in devices_dict.items():
            if not device_id:
                errors.append(AdapterError(
                    error_type="validation",
                    severity="error",
                    message="设备缺少 ID",
                    details={"device": device}
                ))
                continue
            
            device_type = device.get("device_type", "")
            if not device_type:
                errors.append(AdapterError(
                    error_type="validation",
                    severity="error",
                    message=f"设备 {device_id} 缺少设备类型",
                    device_id=device_id
                ))
            
            if device_type == "Node":
                node_count += 1
        
        if node_count == 0:
            errors.append(AdapterError(
                error_type="validation",
                severity="error",
                message="拓扑中没有节点（Node）设备",
                details={}
            ))
        
        # 检查连接
        connections = topology_data.get("connections", [])
        if isinstance(connections, list):
            connections_list = connections
        else:
            connections_list = list(connections.values()) if isinstance(connections, dict) else []
        
        for conn in connections_list:
            from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
            to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
            
            if not from_id or not to_id:
                conn_id = conn.get("id", "unknown") if isinstance(conn, dict) else getattr(conn, "id", "unknown")
                errors.append(AdapterError(
                    error_type="validation",
                    severity="error",
                    message=f"连接 {conn_id} 缺少源或目标设备ID",
                    details={"connection": conn}
                ))
                continue
            
            if from_id not in devices_dict:
                errors.append(AdapterError(
                    error_type="validation",
                    severity="error",
                    message=f"连接引用了不存在的设备: {from_id}",
                    details={"connection": conn}
                ))
            
            if to_id not in devices_dict:
                errors.append(AdapterError(
                    error_type="validation",
                    severity="error",
                    message=f"连接引用了不存在的设备: {to_id}",
                    details={"connection": conn}
                ))
        
        return errors
