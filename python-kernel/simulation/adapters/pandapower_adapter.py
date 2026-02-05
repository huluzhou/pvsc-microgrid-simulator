"""
Pandapower 拓扑数据适配器
将标准拓扑数据格式转换为 pandapower 网络格式
"""

from typing import Dict, Any, List, Optional, Tuple
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
            
            # 连接列表仅表示设备之间的连接关系（from/to），不表示“连接设备”本身
            connections = topology_data.get("connections", [])
            if isinstance(connections, list):
                connections_list = connections
            else:
                connections_list = list(connections.values()) if isinstance(connections, dict) else []
            
            # 第二步：创建连接设备（Line/Transformer 须在 Switch 之前，因开关可能连到线路/变压器）
            for device_id, device in devices_dict.items():
                device_type = device.get("device_type", "")
                if device_type not in ("Line", "Transformer"):
                    continue
                try:
                    self._create_connection_device_from_device(
                        net, device_id, device, bus_map, device_map,
                        connections_list, errors, warnings_list
                    )
                except Exception as e:
                    errors.append(AdapterError(
                        error_type="topology",
                        severity="error",
                        message=f"创建连接设备失败: {str(e)}",
                        device_id=device_id,
                        details={"device": device}
                    ))
            # 第三步：创建开关与功率设备（一次遍历）
            for device_id, device in devices_dict.items():
                device_type = device.get("device_type", "")
                try:
                    if device_type == "Switch":
                        self._create_switch_from_device(
                            net, device_id, device, bus_map, device_map,
                            connections_list, errors, warnings_list
                        )
                    elif device_type in ("Pv", "Load", "Storage", "Charger", "ExternalGrid"):
                        self._create_power_device(
                            net, device_id, device, devices_dict, connections_list,
                            bus_map, device_map, errors, warnings_list
                        )
                except Exception as e:
                    msg = "创建开关失败" if device_type == "Switch" else "创建功率设备失败"
                    errors.append(AdapterError(
                        error_type="topology",
                        severity="error",
                        message=f"{msg}: {str(e)}",
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
        # 获取电压等级：设备详情用 voltage_kv，标准/旧格式用 voltage_level / vn_kv，额定电压用 rated_voltage
        vn_kv = properties.get("voltage_level") or properties.get("vn_kv") or properties.get("voltage_kv") or properties.get("rated_voltage")
        if vn_kv is None:
            vn_kv = self.get_default_value("Node", "voltage_level")
            # 仅当设备已有其他属性但未设置电压等级时告警；properties 为空时静默使用默认值（新建/未编辑的母线）
            if properties:
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
    
    def _get_connected_buses_for_device(
        self,
        device_id: str,
        connections_list: List[Dict[str, Any]],
        bus_map: Dict[str, int],
    ) -> Optional[Tuple[int, int]]:
        """根据连接关系解析连接设备两端对应的母线索引。连接列表元素仅表示设备间连接（from/to），不表示连接设备本身。"""
        neighbor_ids = set()
        for conn in connections_list:
            from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
            to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
            if from_id == device_id and to_id in bus_map:
                neighbor_ids.add(to_id)
            elif to_id == device_id and from_id in bus_map:
                neighbor_ids.add(from_id)
        if len(neighbor_ids) != 2:
            return None
        n1, n2 = list(neighbor_ids)
        return (bus_map[n1], bus_map[n2])
    
    def _create_connection_device_from_device(
        self,
        net,
        device_id: str,
        device: Dict[str, Any],
        bus_map: Dict[str, int],
        device_map: Dict[str, Dict[str, int]],
        connections_list: List[Dict[str, Any]],
        errors: List[AdapterError],
        warnings: List[AdapterError],
    ) -> None:
        """根据设备创建连接设备（Line/Transformer），用 connections 解析两端母线。开关由 _create_switch_from_device 处理。"""
        buses = self._get_connected_buses_for_device(device_id, connections_list, bus_map)
        if buses is None:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"连接设备 {device_id} 必须通过连接关系恰好连接两个母线（Node），请检查 connections",
                device_id=device_id,
                details={"device": device},
            ))
            return
        from_bus, to_bus = buses
        device_type = device.get("device_type", "")
        if device_type == "Line":
            self._create_line(net, device_id, device, from_bus, to_bus, device_map, errors, warnings)
        elif device_type == "Transformer":
            self._create_transformer(net, device_id, device, from_bus, to_bus, device_map, errors, warnings)

    def _get_switch_endpoints(
        self,
        device_id: str,
        connections_list: List[Dict[str, Any]],
        bus_map: Dict[str, int],
        device_map: Dict[str, Dict[str, int]],
    ) -> Optional[Tuple[int, int, str]]:
        """解析开关两端：一端必须为母线，另一端可为母线(b)、线路(l)或变压器(t)。返回 (bus, element, et)。"""
        neighbor_ids = set()
        for conn in connections_list:
            from_id = conn.get("from", "") if isinstance(conn, dict) else getattr(conn, "from_device_id", "")
            to_id = conn.get("to", "") if isinstance(conn, dict) else getattr(conn, "to_device_id", "")
            if from_id == device_id:
                neighbor_ids.add(to_id)
            elif to_id == device_id:
                neighbor_ids.add(from_id)
        if len(neighbor_ids) != 2:
            return None
        a_id, b_id = list(neighbor_ids)
        bus_idx = None
        element_idx = None
        et = None
        if a_id in bus_map and b_id in bus_map:
            bus_idx, element_idx = bus_map[a_id], bus_map[b_id]
            et = "b"
        elif a_id in bus_map and b_id in device_map.get("lines", {}):
            bus_idx, element_idx = bus_map[a_id], device_map["lines"][b_id]
            et = "l"
        elif b_id in bus_map and a_id in device_map.get("lines", {}):
            bus_idx, element_idx = bus_map[b_id], device_map["lines"][a_id]
            et = "l"
        elif a_id in bus_map and b_id in device_map.get("transformers", {}):
            bus_idx, element_idx = bus_map[a_id], device_map["transformers"][b_id]
            et = "t"
        elif b_id in bus_map and a_id in device_map.get("transformers", {}):
            bus_idx, element_idx = bus_map[b_id], device_map["transformers"][a_id]
            et = "t"
        if bus_idx is not None and element_idx is not None and et is not None:
            return (bus_idx, element_idx, et)
        return None

    def _create_switch_from_device(
        self,
        net,
        device_id: str,
        device: Dict[str, Any],
        bus_map: Dict[str, int],
        device_map: Dict[str, Dict[str, int]],
        connections_list: List[Dict[str, Any]],
        errors: List[AdapterError],
        warnings: List[AdapterError],
    ) -> None:
        """根据设备创建开关；两端不一定都是母线，另一端可为线路或变压器。"""
        endpoints = self._get_switch_endpoints(device_id, connections_list, bus_map, device_map)
        if endpoints is None:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"开关 {device_id} 必须通过连接关系连接两端：一端为母线（Node），另一端为母线/线路/变压器",
                device_id=device_id,
                details={"device": device},
            ))
            return
        bus_idx, element_idx, et = endpoints
        self._create_switch(net, device_id, device, bus_idx, element_idx, et, device_map, errors, warnings)

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
                std_type = self.get_default_value("Transformer", "std_type")
                trafo_idx = self.pp.create_transformer(
                    net,
                    hv_bus=from_bus,
                    lv_bus=to_bus,
                    std_type=std_type,
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
                     bus: int, element: int, et: str,
                     device_map: Dict[str, Dict[str, int]],
                     errors: List[AdapterError], warnings: List[AdapterError]):
        """创建开关。et: 'b'=母线-母线, 'l'=母线-线路, 't'=母线-变压器。默认闭合。"""
        properties = device.get("properties", {})
        is_closed = properties.get("is_closed", True)
        if isinstance(is_closed, str):
            is_closed = is_closed.strip().lower() == "true"
        else:
            is_closed = bool(is_closed) if is_closed is not None else True
        try:
            switch_idx = self.pp.create_switch(
                net,
                bus=bus,
                element=element,
                et=et,
                closed=is_closed,
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
            vn_kv = properties.get("voltage_level") or properties.get("vn_kv")
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
        try:
            gen_idx = self.pp.create_sgen(
                net,
                bus=bus,
                p_mw=0.0,
                name=device.get("name", device_id)
            )
            device_map["generators"][device_id] = gen_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建发电机失败: {str(e)}",
                device_id=device_id,
                details={}
            ))
    
    def _create_load(self, net, device_id: str, device: Dict[str, Any],
                    bus: int, device_map: Dict[str, Dict[str, int]],
                    errors: List[AdapterError], warnings: List[AdapterError]):
        """创建负载"""
        try:
            load_idx = self.pp.create_load(
                net,
                bus=bus,
                p_mw=0.0,
                name=device.get("name", device_id)
            )
            device_map["loads"][device_id] = load_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建负载失败: {str(e)}",
                device_id=device_id,
                details={}
            ))
    
    def _create_storage(self, net, device_id: str, device: Dict[str, Any],
                       bus: int, device_map: Dict[str, Dict[str, int]],
                       errors: List[AdapterError], warnings: List[AdapterError]):
        """创建储能设备。并离网模式 grid_mode：0=并网(参与潮流)，1=离网(不参与)，对应 pandapower in_service。"""
        properties = device.get("properties", {})
        
        # 容量：支持 capacity / capacity_kwh（前端设备详情用 capacity_kwh，单位 kWh）-> MWh
        max_e_mwh = properties.get("capacity") or properties.get("capacity_kwh") or 0.0
        if isinstance(max_e_mwh, str):
            try:
                max_e_mwh = float(max_e_mwh) / 1000.0  # kWh -> MWh
            except ValueError:
                max_e_mwh = 0.0
        else:
            max_e_mwh = float(max_e_mwh) / 1000.0 if max_e_mwh else 0.0
        
        # 并离网：0=并网(in_service=True)，1=离网(in_service=False)
        grid_mode = properties.get("grid_mode", 0)
        in_service = (int(grid_mode) == 0)
        # 最大充放电功率与额定功率对齐：rated_power / max_power_kw (kW) -> MW，正=充电上限，负=放电下限
        rated_kw = properties.get("rated_power") or properties.get("max_power_kw") or properties.get("max_power")
        if isinstance(rated_kw, str):
            try:
                rated_kw = float(rated_kw)
            except ValueError:
                rated_kw = 0.0
        else:
            rated_kw = float(rated_kw) if rated_kw else 0.0
        rated_mw = rated_kw / 1000.0 if rated_kw > 0 else 0.0
        power_limits = {}
        if rated_mw > 0:
            power_limits["max_p_mw"] = rated_mw
            power_limits["min_p_mw"] = -rated_mw
        
        try:
            storage_idx = self.pp.create_storage(
                net,
                bus=bus,
                p_mw=0.0,
                max_e_mwh=max_e_mwh,
                name=device.get("name", device_id),
                in_service=in_service,
                **power_limits,
            )
            device_map["storages"][device_id] = storage_idx
        except Exception as e:
            errors.append(AdapterError(
                error_type="topology",
                severity="error",
                message=f"创建储能设备失败: {str(e)}",
                device_id=device_id,
                details={"max_e_mwh": max_e_mwh}
            ))
    
    def _create_external_grid(self, net, device_id: str, device: Dict[str, Any],
                             bus: int, errors: List[AdapterError], warnings: List[AdapterError]):
        """创建外部电网"""
        properties = device.get("properties", {})
        
        vn_kv = properties.get("voltage_level") or properties.get("vn_kv") or 10.0
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
