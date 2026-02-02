"""
仿真引擎核心
"""

import threading
import time
import hashlib
import json
from typing import Dict, Any, List, Optional
from .power_calculation.factory import PowerKernelFactory
from .adapters.pandapower_adapter import PandapowerTopologyAdapter
from .adapters.topology_adapter import AdapterError


class SimulationEngine:
    """仿真引擎"""
    
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        
        # 拓扑数据管理
        self.topology_data: Optional[Dict[str, Any]] = None
        self.topology_hash: Optional[str] = None  # 拓扑数据哈希值，用于判断是否需要重新创建网络
        
        # 计算内核和适配器
        self.power_calculator = None
        self.topology_adapter = None
        
        # 网络对象缓存
        self.cached_network = None  # 缓存的pandapower网络对象
        self.cached_bus_map: Dict[str, int] = {}  # 设备ID到母线索引的映射
        self.cached_device_map: Dict[str, Dict[str, int]] = {}  # 设备ID到pandapower元素索引的映射
        
        # 周期性计算相关
        self.calculation_thread: Optional[threading.Thread] = None
        self.calculation_interval_ms = 1000  # 默认1秒
        self.calculation_count = 0
        self.last_calculation_time = 0.0
        self.calculation_errors: List[Dict[str, Any]] = []
        
        # 计算结果缓存
        self.last_calculation_result: Optional[Dict[str, Any]] = None
    
    def set_topology(self, topology_data: Dict[str, Any], kernel_type: str = "pandapower"):
        """
        设置拓扑数据
        
        Args:
            topology_data: 标准拓扑数据格式
            kernel_type: 计算内核类型（默认pandapower）
        """
        # 计算拓扑数据哈希值（只考虑结构，不考虑功率值等变化的数据）
        topology_structure = self._extract_topology_structure(topology_data)
        new_hash = self._calculate_topology_hash(topology_structure)
        
        # 如果拓扑结构发生变化，清除缓存并重新创建网络
        if new_hash != self.topology_hash:
            self.topology_hash = new_hash
            self.cached_network = None
            self.cached_bus_map = {}
            self.cached_device_map = {}
        
        self.topology_data = topology_data
        
        # 使用工厂同时创建计算内核和适配器（如果可用）
        try:
            kernel_and_adapter = PowerKernelFactory.create_with_adapter(kernel_type)
        except Exception:
            kernel_and_adapter = None
        if kernel_and_adapter:
            self.power_calculator, self.topology_adapter = kernel_and_adapter
            if self.topology_adapter is None:
                # 如果没有对应的适配器，使用默认的pandapower适配器（向后兼容）
                try:
                    self.topology_adapter = PandapowerTopologyAdapter()
                except Exception as e:
                    raise RuntimeError(
                        f"无法创建拓扑适配器: {e}. "
                        "请在本机 Python 环境中执行: pip install -r python-kernel/requirements.txt"
                    ) from e
        else:
            # 回退到单独创建
            if self.topology_adapter is None:
                try:
                    self.topology_adapter = PandapowerTopologyAdapter()
                except Exception as e:
                    raise RuntimeError(
                        f"无法创建拓扑适配器: {e}. "
                        "请在本机 Python 环境中执行: pip install -r python-kernel/requirements.txt"
                    ) from e
            if self.power_calculator is None:
                self.power_calculator = PowerKernelFactory.create(kernel_type)
                if not self.power_calculator:
                    raise RuntimeError(f"无法创建功率计算内核: {kernel_type}")
    
    def _extract_topology_structure(self, topology_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取拓扑结构信息（排除功率值等变化的数据）
        
        只保留：
        - 设备类型、连接关系
        - 固定参数（电压等级、线路长度、变压器参数等）
        排除：
        - 功率值（rated_power等，这些会随时间变化）
        """
        devices = topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        
        # 提取结构信息
        structure_devices = {}
        for device_id, device in devices_dict.items():
            device_type = device.get("device_type", "")
            properties = device.get("properties", {})
            
            # 只保留结构相关的属性，排除功率值
            structure_properties = {}
            for key, value in properties.items():
                # 保留固定参数，排除功率相关参数
                if key not in ["rated_power", "p_mw", "q_mvar", "p_kw", "q_kvar"]:
                    structure_properties[key] = value
            
            structure_devices[device_id] = {
                "device_type": device_type,
                "name": device.get("name", ""),
                "properties": structure_properties
            }
        
        return {
            "devices": structure_devices,
            "connections": topology_data.get("connections", [])
        }
    
    def _calculate_topology_hash(self, topology_structure: Dict[str, Any]) -> str:
        """计算拓扑结构的哈希值"""
        # 将拓扑结构序列化为JSON字符串（排序以确保一致性）
        structure_str = json.dumps(topology_structure, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(structure_str.encode('utf-8')).hexdigest()
    
    def set_device_mode(self, device_id: str, mode: str):
        """
        设置设备工作模式（已弃用，保留用于兼容性）
        
        注意：设备功率值现在直接从拓扑数据的 properties 中读取
        """
        pass  # 不再需要模式管理，功率值从拓扑数据中获取

    def update_device_properties(self, device_id: str, properties: Dict[str, Any]) -> None:
        """
        事件驱动远程控制：将设备属性增量立即写入当前拓扑数据，下一拍 _update_network_power_values 即生效。
        避免轮询导致的初始时刻指令缺失或初值与预期不符。
        """
        if not self.topology_data:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            for d in devices:
                if d.get("id") == device_id:
                    props = d.setdefault("properties", {})
                    props.update(properties)
                    return
        else:
            if device_id in devices:
                props = devices[device_id].setdefault("properties", {})
                props.update(properties)
    
    def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """
        获取设备数据
        
        注意：此方法已简化，设备数据应从计算结果中获取
        """
        # 如果仿真运行中且有计算结果，从计算结果中获取
        if self.is_running and self.last_calculation_result and self.topology_data:
            devices_result = self.last_calculation_result.get("devices", {})
            devices_dict = self.topology_data.get("devices", {})
            
            if isinstance(devices_dict, list):
                devices_dict = {d.get("id", ""): d for d in devices_dict if d.get("id")}
            
            device = devices_dict.get(device_id)
            if not device:
                return {
                    "voltage": 0.0,
                    "current": 0.0,
                    "power": 0.0,
                    "timestamp": time.time(),
                }
            
            device_type = device.get("device_type", "")
            device_name = device.get("name", "")
            result_data = {}
            
            # 根据设备类型从计算结果中提取数据
            if device_type == "Node":
                # Node设备对应Bus，使用bus_map查找
                if device_id in self.cached_bus_map:
                    bus_idx = self.cached_bus_map[device_id]
                    buses = devices_result.get("buses", {})
                    if isinstance(buses, dict) and str(bus_idx) in buses:
                        bus_data = buses[str(bus_idx)]
                        vm_pu = bus_data.get("vm_pu", 0.0)
                        voltage_level = device.get("properties", {}).get("voltage_level", 0.4)
                        result_data["voltage"] = vm_pu * voltage_level * 1000.0  # 转换为V
                        result_data["voltage_pu"] = vm_pu
                        result_data["angle"] = bus_data.get("va_degree", 0.0)
            
            elif device_type == "Line":
                # Line设备，使用device_map查找
                if device_id in self.cached_device_map.get("lines", {}):
                    line_idx = self.cached_device_map["lines"][device_id]
                    lines = devices_result.get("lines", {})
                    if isinstance(lines, dict) and str(line_idx) in lines:
                        line_data = lines[str(line_idx)]
                        result_data["p_from_mw"] = line_data.get("p_from_mw", 0.0)
                        result_data["q_from_mvar"] = line_data.get("q_from_mvar", 0.0)
                        result_data["p_to_mw"] = line_data.get("p_to_mw", 0.0)
                        result_data["q_to_mvar"] = line_data.get("q_to_mvar", 0.0)
                        result_data["i_from_ka"] = line_data.get("i_from_ka", 0.0)
                        result_data["i_to_ka"] = line_data.get("i_to_ka", 0.0)
                        result_data["loading_percent"] = line_data.get("loading_percent", 0.0)
            
            elif device_type == "Transformer":
                # Transformer设备
                if device_id in self.cached_device_map.get("transformers", {}):
                    trafo_idx = self.cached_device_map["transformers"][device_id]
                    transformers = devices_result.get("transformers", {})
                    if isinstance(transformers, dict) and str(trafo_idx) in transformers:
                        trafo_data = transformers[str(trafo_idx)]
                        result_data["p_hv_mw"] = trafo_data.get("p_hv_mw", 0.0)
                        result_data["q_hv_mvar"] = trafo_data.get("q_hv_mvar", 0.0)
                        result_data["p_lv_mw"] = trafo_data.get("p_lv_mw", 0.0)
                        result_data["q_lv_mvar"] = trafo_data.get("q_lv_mvar", 0.0)
                        result_data["loading_percent"] = trafo_data.get("loading_percent", 0.0)
            
            elif device_type == "Load":
                # Load设备
                if device_id in self.cached_device_map.get("loads", {}):
                    load_idx = self.cached_device_map["loads"][device_id]
                    loads = devices_result.get("loads", {})
                    if isinstance(loads, dict) and str(load_idx) in loads:
                        load_data = loads[str(load_idx)]
                        result_data["p_mw"] = load_data.get("p_mw", 0.0)
                        result_data["q_mvar"] = load_data.get("q_mvar", 0.0)
            
            elif device_type == "Pv":
                # Pv设备对应Generator
                if device_id in self.cached_device_map.get("generators", {}):
                    gen_idx = self.cached_device_map["generators"][device_id]
                    generators = devices_result.get("generators", {})
                    if isinstance(generators, dict) and str(gen_idx) in generators:
                        gen_data = generators[str(gen_idx)]
                        result_data["p_mw"] = gen_data.get("p_mw", 0.0)
                        result_data["q_mvar"] = gen_data.get("q_mvar", 0.0)
            
            elif device_type == "Storage":
                # Storage设备
                if device_id in self.cached_device_map.get("storages", {}):
                    storage_idx = self.cached_device_map["storages"][device_id]
                    storages = devices_result.get("storages", {})
                    if isinstance(storages, dict) and str(storage_idx) in storages:
                        storage_data = storages[str(storage_idx)]
                        result_data["p_mw"] = storage_data.get("p_mw", 0.0)
                        result_data["q_mvar"] = storage_data.get("q_mvar", 0.0)
            
            if result_data:
                result_data["timestamp"] = time.time()
                result_data["device_id"] = device_id
                result_data["device_name"] = device_name
                result_data["device_type"] = device_type
                return result_data
        
        # 返回默认值
        return {
            "voltage": 0.0,
            "current": 0.0,
            "power": 0.0,
            "timestamp": time.time(),
        }
    
    def _calculation_loop(self):
        """
        周期性计算循环（已弃用）
        
        注意：此方法已不再使用。计算现在由Rust端主动触发，
        通过调用 perform_calculation 方法来实现。
        这样可以避免Python端和Rust端循环不同步导致的时序问题。
        """
        # 保留方法定义以保持接口兼容性，但不再执行任何操作
        pass
    
    def perform_calculation(self) -> Dict[str, Any]:
        """
        执行一次计算（由Rust端主动调用）
        
        返回:
            计算结果字典
        """
        if not self.is_running:
            return {
                "converged": False,
                "errors": [{
                    "type": "runtime",
                    "severity": "error",
                    "message": "仿真未启动",
                    "details": {}
                }],
                "devices": {}
            }
        
        if self.is_paused:
            # 暂停时返回上次结果
            return self.last_calculation_result or {
                "converged": False,
                "errors": [],
                "devices": {}
            }
        
        try:
            # 执行一次计算
            result = self._perform_calculation()
            self.last_calculation_result = result
            self.calculation_count += 1
            self.last_calculation_time = time.time()
            
            # 更新错误列表：只保留当前计算的错误，不累积历史错误
            # 如果需要查看历史错误，应该通过日志系统而不是内存累积
            if "errors" in result:
                self.calculation_errors = result["errors"]
            else:
                self.calculation_errors = []
            
            return result
        except Exception as e:
            # 记录错误，并标记需自动停止
            error_info = {
                "type": "runtime",
                "severity": "error",
                "message": f"计算异常: {str(e)}",
                "timestamp": time.time(),
                "details": {"exception": str(e), "type": type(e).__name__}
            }
            self.calculation_errors = [error_info]
            self.is_paused = True
            return {
                "converged": False,
                "errors": [error_info],
                "devices": {},
                "auto_paused": True
            }
    
    def _perform_calculation(self) -> Dict[str, Any]:
        """执行一次潮流计算"""
        if not self.topology_data:
            raise ValueError("拓扑数据未设置")
        
        if not self.topology_adapter:
            raise ValueError("拓扑适配器未初始化")
        
        if not self.power_calculator:
            raise ValueError("计算内核未初始化")
        
        errors: List[Dict[str, Any]] = []
        
        # 如果网络对象已缓存，直接使用；否则重新创建
        if self.cached_network is None:
            # 使用适配器转换拓扑数据（只在拓扑结构变化时执行）
            adapter_result = self.topology_adapter.convert(self.topology_data)
            
            # 收集适配器错误
            for err in adapter_result.errors:
                errors.append({
                    "type": err.error_type,
                    "severity": err.severity,
                    "message": err.message,
                    "device_id": err.device_id,
                    "details": err.details or {},
                    "timestamp": time.time()
                })
            
            for warn in adapter_result.warnings:
                errors.append({
                    "type": warn.error_type,
                    "severity": warn.severity,
                    "message": warn.message,
                    "device_id": warn.device_id,
                    "details": warn.details or {},
                    "timestamp": time.time()
                })
            
            # 如果适配器转换失败，返回错误并标记需自动停止
            if not adapter_result.success:
                self.is_paused = True
                return {
                    "converged": False,
                    "errors": errors,
                    "devices": {},
                    "auto_paused": True
                }
            
            # 缓存网络对象
            self.cached_network = adapter_result.data
            
            # 从适配器获取映射信息（如果适配器支持）
            if hasattr(self.topology_adapter, 'get_bus_map'):
                self.cached_bus_map = self.topology_adapter.get_bus_map()
            if hasattr(self.topology_adapter, 'get_device_map'):
                self.cached_device_map = self.topology_adapter.get_device_map()
        
        # 更新网络中的功率值（从设备模式获取当前功率值）
        self._update_network_power_values()
        
        # 执行潮流计算（使用缓存的网络对象）
        try:
            calculation_result = self.power_calculator.calculate_power_flow(self.cached_network)
            
            # 合并错误信息
            if "errors" in calculation_result:
                errors.extend(calculation_result["errors"])
            
            converged = calculation_result.get("converged", False)

            # 错误去重：按 (type, severity, message, device_id, details) 维度去重
            # 避免同一条错误在每次计算中被重复加入，导致错误数量无限增加。
            unique_errors: List[Dict[str, Any]] = []
            seen_keys = set()
            for err in errors:
                key = (
                    err.get("type"),
                    err.get("severity"),
                    err.get("message"),
                    err.get("device_id"),
                    json.dumps(err.get("details", {}), sort_keys=True, ensure_ascii=False),
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                unique_errors.append(err)
            errors = unique_errors

            # 检查是否存在严重错误（severity == "error"），并判断是否需要自动暂停
            has_critical_error = any(
                err.get("severity") == "error"
                for err in errors
            )
            # 只要计算未收敛，或者存在严重错误，就认为需要自动暂停，
            # 防止在拓扑/参数有问题时周期性重复计算产生大量重复错误。
            should_auto_pause = has_critical_error or not converged

            # 如果需要自动暂停，清空缓存并暂停仿真，避免持续报错
            if should_auto_pause:
                # 清空缓存强制下次重新适配
                self.cached_network = None
                self.cached_bus_map = {}
                self.cached_device_map = {}
                
                # 自动暂停仿真，避免周期性计算持续产生相同错误
                self.is_paused = True
                if errors:
                    print(f"检测到严重错误或计算未收敛，已自动暂停仿真：{errors[0].get('message', '未知错误')}")
                else:
                    print("检测到计算未收敛，已自动暂停仿真")
            
            return {
                "converged": converged,
                "errors": errors,
                "devices": calculation_result.get("devices", {}),
                "auto_paused": should_auto_pause  # 标记是否自动暂停
            }
            
        except Exception as e:
            errors.append({
                "type": "calculation",
                "severity": "error",
                "message": f"潮流计算失败: {str(e)}",
                "details": {"exception": str(e), "type": type(e).__name__},
                "timestamp": time.time()
            })
            
            # 计算异常，清空缓存强制下次重新适配
            self.cached_network = None
            self.cached_bus_map = {}
            self.cached_device_map = {}
            
            # 自动暂停仿真，避免周期性计算持续产生相同错误
            self.is_paused = True
            print(f"计算异常，已自动暂停仿真：{str(e)}")
            
            return {
                "converged": False,
                "errors": errors,
                "devices": {},
                "auto_paused": True  # 标记已自动暂停
            }
    
    def _update_network_power_values(self):
        """
        更新网络中的功率值（从拓扑数据的 properties 中读取）
        
        只更新会变化的功率值，不重新创建网络结构
        功率值应该由外部（Rust端或前端）通过更新拓扑数据来设置
        """
        if not self.cached_network:
            return
        
        try:
            import pandapower as pp
            
            # 获取设备字典
            devices = self.topology_data.get("devices", {})
            if isinstance(devices, list):
                devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
            else:
                devices_dict = devices
            
            # 更新各设备的功率值（从拓扑数据的 properties 中读取）
            for device_id, device in devices_dict.items():
                device_type = device.get("device_type", "")
                properties = device.get("properties", {})
                
                # 从 properties 中获取功率值（单位：kW）
                # 支持多种属性名：rated_power, p_kw, power
                p_kw = 0.0
                if "rated_power" in properties:
                    p_kw = float(properties["rated_power"])
                elif "p_kw" in properties:
                    p_kw = float(properties["p_kw"])
                elif "power" in properties:
                    power_val = properties["power"]
                    if isinstance(power_val, (int, float)):
                        p_kw = float(power_val)
                        # 如果值很大（>1000），假设单位是W，转换为kW
                        if abs(p_kw) > 1000:
                            p_kw = p_kw / 1000.0
                
                # 转换为MW（pandapower使用MW）
                p_mw = p_kw / 1000.0
                
                # 根据设备类型更新对应的功率值
                if device_type == "Pv":
                    # 更新发电机功率
                    if device_id in self.cached_device_map.get("generators", {}):
                        gen_idx = self.cached_device_map["generators"][device_id]
                        if 0 <= gen_idx < len(self.cached_network.gen):
                            self.cached_network.gen.at[gen_idx, "p_mw"] = p_mw
                
                elif device_type == "Load":
                    # 更新负载功率
                    if device_id in self.cached_device_map.get("loads", {}):
                        load_idx = self.cached_device_map["loads"][device_id]
                        if 0 <= load_idx < len(self.cached_network.load):
                            self.cached_network.load.at[load_idx, "p_mw"] = p_mw
                
                elif device_type == "Storage":
                    # 更新储能功率
                    if device_id in self.cached_device_map.get("storages", {}):
                        storage_idx = self.cached_device_map["storages"][device_id]
                        if 0 <= storage_idx < len(self.cached_network.storage):
                            self.cached_network.storage.at[storage_idx, "p_mw"] = p_mw
                
                elif device_type == "Charger":
                    # 更新充电桩功率（作为负载处理）
                    if device_id in self.cached_device_map.get("loads", {}):
                        load_idx = self.cached_device_map["loads"][device_id]
                        if 0 <= load_idx < len(self.cached_network.load):
                            self.cached_network.load.at[load_idx, "p_mw"] = p_mw
                            
        except Exception as e:
            # 更新功率值失败不影响计算，只记录警告
            pass
    
    def start(self, calculation_interval_ms: int = 1000):
        """
        启动仿真
        
        注意：为了与Rust端同步，Python端不再启动自己的循环
        Rust端会主动调用 perform_calculation 来触发计算
        这样可以避免时序问题，确保Rust端获取的是最新计算结果
        """
        # 每次 start 调用都重置计数与暂停状态，支持「暂停后再点启动」从 0 重新计时
        self.calculation_count = 0
        self.is_paused = False
        if self.is_running:
            return
        if not self.topology_data:
            raise ValueError("请先设置拓扑数据")
        
        self.is_running = True
        self.calculation_interval_ms = calculation_interval_ms
        self.calculation_errors = []
        
        # 不再启动独立的计算线程，由Rust端控制计算节奏
        # 这样可以避免时序问题，确保Rust端获取的是最新计算结果
    
    def stop(self):
        """停止仿真"""
        self.is_running = False
        self.is_paused = False
        
        # 等待计算线程结束
        if self.calculation_thread and self.calculation_thread.is_alive():
            self.calculation_thread.join(timeout=2.0)
        
        self.calculation_thread = None
        
        # 注意：不清除网络缓存，以便下次启动时复用
        # 只有在拓扑结构变化时才会清除缓存
    
    def pause(self):
        """暂停仿真"""
        self.is_paused = True
    
    def resume(self):
        """恢复仿真"""
        self.is_paused = False
    
    def get_calculation_status(self) -> Dict[str, Any]:
        """获取计算状态"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "calculation_count": self.calculation_count,
            "calculation_interval_ms": self.calculation_interval_ms,
            "last_calculation_time": self.last_calculation_time,
            "error_count": len(self.calculation_errors)
        }
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """获取错误列表"""
        return self.calculation_errors.copy()
    
    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """获取最后一次计算结果"""
        return self.last_calculation_result
