"""
仿真引擎核心
"""

import random
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

        # 随机模式设备配置：device_id -> {"min_power": float, "max_power": float}（单位 kW）
        self.device_random_config: Dict[str, Dict[str, float]] = {}
        # 设备模式（manual / random_data / historical_data），用于统一后端更新时按模式写 properties
        self.device_modes: Dict[str, str] = {}
        # 手动模式当前设定：device_id -> {"p_kw": float, "q_kvar": float}（单位 kW/kVar）
        self.device_manual_setpoint: Dict[str, Dict[str, float]] = {}
        # 远程控制设定（如 Modbus 写入）：device_id -> {"p_kw": float, "q_kvar": float}，最后应用以覆盖随机/历史
        self.device_remote_setpoint: Dict[str, Dict[str, float]] = {}
        # 历史模式配置：device_id -> config dict
        self.device_historical_config: Dict[str, Dict[str, Any]] = {}
        # 历史数据 Provider 缓存：device_id -> HistoricalDataProvider 实例
        self.device_historical_providers: Dict[str, Any] = {}
        # 历史回放当前索引：device_id -> 当前数据点索引
        self.device_historical_index: Dict[str, int] = {}
        # 历史回放上次更新时间（秒）：device_id -> 上次从历史数据读取的仿真时间
        self.device_historical_last_update: Dict[str, float] = {}

        # 设备级仿真参数：device_id -> {"samplingIntervalMs", "responseDelayMs", "measurementErrorPct"}
        self.device_sim_params: Dict[str, Dict[str, float]] = {}
        # 设备响应延迟 pending 队列：device_id -> [{target_props, apply_at}]
        self.device_pending_commands: Dict[str, List[Dict[str, Any]]] = {}
        # 仿真累计时间（秒），每步累加
        self.sim_elapsed_seconds: float = 0.0
    
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
        self.device_random_config.clear()
        self.device_modes.clear()
        self.device_manual_setpoint.clear()
        self.device_remote_setpoint.clear()
        self.device_historical_config.clear()
        self.device_historical_providers.clear()
        self.device_historical_index.clear()
        self.device_historical_last_update.clear()
        self.device_sim_params.clear()
        self.device_pending_commands.clear()
        self.sim_elapsed_seconds = 0.0

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
    
    def set_device_mode(self, device_id: str, mode: str) -> None:
        """
        设置设备工作模式。与 set_device_*_config 配合，供统一后端每步写 properties 时按模式取值。
        """
        self.device_modes[device_id] = mode

    def set_device_manual_setpoint(self, device_id: str, active_power: float, reactive_power: float) -> None:
        """
        设置手动模式设备的当前功率设定（kW / kVar）。
        每步计算前会将该设定写入设备 properties。
        """
        self.device_manual_setpoint[device_id] = {
            "p_kw": float(active_power),
            "q_kvar": float(reactive_power),
        }

    def set_device_historical_config(self, device_id: str, config: Dict[str, Any]) -> None:
        """
        设置历史模式设备配置并创建 Provider 实例。
        config 中 sourceType='csv'|'sqlite'，filePath 等字段传给 Provider。
        """
        from .historical_data import create_provider
        self.device_historical_config[device_id] = dict(config) if config else {}
        self.device_historical_index[device_id] = 0
        self.device_historical_last_update[device_id] = 0.0
        if config:
            provider = create_provider(config)
            if provider:
                self.device_historical_providers[device_id] = provider
            else:
                self.device_historical_providers.pop(device_id, None)
        else:
            self.device_historical_providers.pop(device_id, None)

    def set_device_sim_params(self, device_id: str, params: Dict[str, Any]) -> None:
        """
        设置设备级仿真参数。
        params: {"samplingIntervalMs": float, "responseDelayMs": float, "measurementErrorPct": float}
        """
        self.device_sim_params[device_id] = {
            "samplingIntervalMs": float(params.get("samplingIntervalMs", 0)),
            "responseDelayMs": float(params.get("responseDelayMs", 0)),
            "measurementErrorPct": float(params.get("measurementErrorPct", 0)),
        }

    def set_device_random_config(self, device_id: str, min_power: float, max_power: float) -> None:
        """
        设置随机模式设备的功率范围（单位 kW）。
        每步计算前会在此范围内生成新的有功功率并写入设备 properties。
        """
        self.device_random_config[device_id] = {
            "min_power": float(min_power),
            "max_power": float(max_power),
        }

    def update_switch_state(self, device_id: str, is_closed: bool) -> None:
        """
        更新开关的闭合/断开状态，同时更新 topology_data 和 pandapower 网络。
        """
        if not self.topology_data:
            return
        
        # 更新 topology_data 中的 properties
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        
        device = devices_dict.get(device_id)
        if not device:
            return
        
        props = device.setdefault("properties", {})
        props["is_closed"] = is_closed
        
        # 更新 pandapower 网络中的开关状态
        if self.cached_network and self.cached_device_map:
            device_map = self.cached_device_map.get("switches", {})
            switch_idx = device_map.get(device_id)
            if switch_idx is not None:
                try:
                    # pandapower 网络中 switch 表的 closed 列控制开关状态
                    self.cached_network.switch.at[switch_idx, "closed"] = is_closed
                except Exception as e:
                    print(f"更新开关 {device_id} 状态失败: {e}")

    def _parse_power_from_properties(self, properties: Dict[str, Any]) -> Optional[tuple]:
        """从 properties 解析 (p_kw, q_kvar)，无功率字段时返回 None。"""
        if "rated_power" in properties:
            p_kw = float(properties["rated_power"])
        elif "p_kw" in properties:
            p_kw = float(properties["p_kw"])
        else:
            return None
        q_kvar = float(properties.get("q_kvar", 0))
        return (p_kw, q_kvar)

    def update_device_properties(self, device_id: str, properties: Dict[str, Any]) -> None:
        """
        事件驱动远程控制：将属性增量写入当前拓扑的 device.properties，下一拍计算即生效。

        数据源与触发式约定：
        - 手动/随机/历史：数据源，每步写 properties.p_kw，不在此处改写数据源缓存。
        - Modbus on_off/power_limit：触发式过滤，只写 properties；仅储能的 set_power 写 device_remote_setpoint。

        逻辑概要：
        1. 有功功率限制与百分比限制互斥：写入 power_limit_raw 时清除 power_limit_pct，写入 power_limit_pct 时清除 power_limit_raw，只响应最新一条。
        2. 合并 properties 到拓扑对应设备的 props。
        3. 手动模式：仅在“用户设定功率”时同步 device_manual_setpoint；Modbus 关机（on_off=0）不覆盖，保证 5005 先 0 再 1 后功率可恢复。
        4. 储能：set_power（HR4）写入 device_remote_setpoint；光伏/充电桩开机（on_off=1）时清除 device_remote_setpoint 残留。
        """
        if not self.topology_data:
            return
        devices = self.topology_data.get("devices", {})
        devices_dict = {d.get("id", ""): d for d in devices if d.get("id")} if isinstance(devices, list) else devices
        if device_id not in devices_dict:
            return

        # 响应延迟：如果该设备配置了 responseDelayMs > 0，将属性放入 pending 队列延迟生效
        delay_ms = self.device_sim_params.get(device_id, {}).get("responseDelayMs", 0)
        if delay_ms > 0:
            apply_at = self.sim_elapsed_seconds + delay_ms / 1000.0
            self.device_pending_commands.setdefault(device_id, []).append({
                "target_props": dict(properties),
                "apply_at": apply_at,
            })
            return  # 延迟生效，不立即写入

        device = devices_dict[device_id]
        props = device.setdefault("properties", {})
        # 有功功率限制与百分比限制互斥：只响应最新一条，写入一种时清除另一种
        if "power_limit_raw" in properties:
            props.pop("power_limit_pct", None)
        if "power_limit_pct" in properties:
            props.pop("power_limit_raw", None)
        # 无功控制事件互斥：写功率因数(5041)时清除无功百分比(5040)，写无功百分比(5040)时清除功率因数(5041)，一个指令不受另一个影响
        if "power_factor" in properties:
            props.pop("reactive_comp_pct", None)
        if "reactive_comp_pct" in properties:
            props.pop("power_factor", None)
        props.update(properties)

        power_tuple = self._parse_power_from_properties(properties)
        device_type = device.get("device_type", "")
        is_shutdown = properties.get("on_off") == 0

        # 1) 手动模式：仅用户设定功率时同步；Modbus 关机指令不覆盖手动设定
        if self.device_modes.get(device_id) == "manual" and power_tuple is not None and not is_shutdown:
            p_kw, q_kvar = power_tuple
            self.device_manual_setpoint[device_id] = {"p_kw": p_kw, "q_kvar": q_kvar}

        # 2) 储能 set_power → device_remote_setpoint；光伏/充电桩 on_off=1 → 清除 remote 残留
        if device_type == "Storage" and power_tuple is not None:
            p_kw, q_kvar = power_tuple
            self.device_remote_setpoint[device_id] = {"p_kw": p_kw, "q_kvar": q_kvar}
        elif device_type != "Storage" and properties.get("on_off") not in (None, 0):
            self.device_remote_setpoint.pop(device_id, None)
    
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
        执行一次仿真计算 - 四阶段数据流
        
        ┌──────────────────────────────────────────────────────────────────┐
        │ 第1阶段：应用三类原始数据源（优先级递增，后者覆盖前者）          │
        │ (_apply_device_power_sources)                                   │
        │                                                                  │
        │ - 手动设定 (_apply_manual_power_values)                         │
        │ - 随机数据源 (_apply_random_power_values)                       │
        │ - 历史数据源 (_apply_historical_power_values)                   │
        │                                                                  │
        │ 结果：各设备 properties.p_kw/q_kvar = 原始功率                  │
        └──────────────────────────────────────────────────────────────────┘
                                    ↓
        ┌──────────────────────────────────────────────────────────────────┐
        │ 第2阶段：应用 Modbus 远程控制指令（所有过滤逻辑在此完成）       │
        │ (_apply_modbus_instructions)                                    │
        │                                                                  │
        │ 包含两类指令的完整处理：                                        │
        │ 1) 设定指令（HR4 set_power，仅储能）                           │
        │    → 直接覆盖 properties.p_kw                                   │
        │ 2) 限制指令（所有设备类型）                                    │
        │    → 应用 _apply_modbus_filtering 过滤                         │
        │    - on_off / power_limit_pct / power_limit_raw 等             │
        │    → properties.p_kw = min(p_kw, limit)                        │
        │                                                                  │
        │ 结果：各设备 properties.p_kw/q_kvar = 最终过滤后功率            │
        └──────────────────────────────────────────────────────────────────┘
                                    ↓
        ┌──────────────────────────────────────────────────────────────────┐
        │ 第3阶段：更新网络功率值（纯网络更新，无任何过滤）              │
        │ (_update_network_power_values)                                  │
        │                                                                  │
        │ - 读取 properties 中的最终功率值（额定/限制在第2阶段完成，     │
        │   额定容量从拓扑 max_power_kw/rated_power 获取）                │
        │ - 写入 pandapower 网络各表（sgen/load/storage）                │
        │                                                                  │
        │ 结果：pandapower 网络已准备完毕                                 │
        └──────────────────────────────────────────────────────────────────┘
                                    ↓
        ┌──────────────────────────────────────────────────────────────────┐
        │ 第4阶段：执行潮流计算 & 更新状态                               │
        └──────────────────────────────────────────────────────────────────┘
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
        
        # 仿真时间累加（秒），用于历史回放和响应延迟
        dt_sec = self.calculation_interval_ms / 1000.0
        self.sim_elapsed_seconds += dt_sec
        # 历史回放采样控制：按 playbackIntervalMs 间隔更新数据索引（见 _apply_historical_power_values）
        # 处理响应延迟 pending 队列：到时间的命令写入 properties
        self._flush_pending_commands()
        # 第1阶段：应用三类原始数据源（手动 -> 随机 -> 历史）
        self._apply_device_power_sources()
        # 第2阶段：应用 Modbus 远程控制指令（set_power + 限制过滤）
        self._apply_modbus_instructions()
        # 第3阶段：更新网络功率值（读 properties，光伏 power_limit_pct 精确计算，写网络）
        self._update_network_power_values()
        # 第4阶段：执行潮流计算（使用缓存的网络对象）
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
            
            # 第5阶段：潮流计算后按设备叠加测量误差到 properties（噪声不影响潮流本身）
            if converged:
                self._apply_measurement_noise()

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
    
    def _apply_device_power_sources(self) -> None:
        """
        第1阶段：应用三类原始数据源。顺序：手动 -> 随机 -> 历史（后写覆盖先写）。
        远程（Modbus set_power）在第2阶段 _apply_modbus_instructions 中处理。
        """
        self._apply_manual_power_values()
        self._apply_random_power_values()
        self._apply_historical_power_values()

    def _apply_modbus_instructions(self) -> None:
        """
        第2阶段：应用 Modbus 远程控制指令（所有过滤逻辑在此完成）。
        1) 设定指令（HR4 set_power，仅储能）-> 直接覆盖 properties.p_kw
        2) 限制指令（所有设备）-> _apply_modbus_filtering -> properties.p_kw = min(p_kw, limit)
        """
        if not self.topology_data:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        # 1) 设定指令：储能的 set_power 寄存器
        if self.device_remote_setpoint:
            for device_id, cfg in self.device_remote_setpoint.items():
                device = devices_dict.get(device_id)
                if not device:
                    continue
                p_kw = cfg.get("p_kw", 0.0)
                q_kvar = cfg.get("q_kvar", 0.0)
                props = device.setdefault("properties", {})
                props["p_kw"] = p_kw
                props["q_kvar"] = q_kvar
        # 2) 限制指令过滤：对所有设备应用 on_off / power_limit_pct / power_limit_raw 等；当前功率只读 p_kw（额定功率仅从拓扑获取）
        for device_id, device in devices_dict.items():
            device_type = device.get("device_type", "")
            properties = device.get("properties", {})
            p_kw = float(properties.get("p_kw", 0.0))
            q_kvar = float(properties.get("q_kvar", 0.0))
            p_kw, q_kvar = self._apply_modbus_filtering(device_type, properties, p_kw, q_kvar)
            properties["p_kw"] = p_kw
            properties["q_kvar"] = q_kvar

    def _apply_modbus_filtering(self, device_type: str, properties: dict, p_kw: float, q_kvar: float) -> tuple:
        """
        统一 Modbus 限制指令过滤：on_off、power_limit_pct、power_limit_raw、reactive_comp_pct/power_factor。
        百分比限制的基准功率从拓扑额定容量取：rated_power_kw / max_power_kw（不用 rated_power，以免被手动设定覆盖）。
        返回 (p_kw, q_kvar)。
        """
        on_off = properties.get("on_off", 1)
        if on_off == 0:
            p_kw = 0.0
            q_kvar = 0.0
        if "power_limit_pct" in properties:
            # 额定容量优先用拓扑 nameplate，避免 rated_power 被手动设定覆盖导致百分比不起效
            nominal_kw = float(
                properties.get("rated_power_kw")
                or properties.get("max_power_kw")
                or properties.get("rated_power")
                or 0
            )
            if nominal_kw > 0:
                pct = float(properties["power_limit_pct"])
                p_kw = min(p_kw, nominal_kw * pct / 100.0)
        if "power_limit_raw" in properties:
            raw = int(properties["power_limit_raw"]) & 0xFFFF
            cap_kw = raw / 10.0
            p_kw = min(p_kw, cap_kw)
        if device_type == "Pv" and "power_factor" in properties:
            # HR 5041：功率因数寄存器 800~1000 表示 0.8~1，-1000~-800 表示 -1~-0.8（超前）
            raw_pf = int(properties["power_factor"])
            raw_pf = raw_pf if raw_pf <= 32767 else raw_pf - 65536
            pf = raw_pf / 1000.0
            if (0.8 <= pf <= 1.0) or (-1.0 <= pf <= -0.8):
                q_mag = abs(p_kw * ((1 - pf ** 2) ** 0.5) / pf) if pf != 0 else 0.0
                q_kvar = q_mag if pf >= 0 else -q_mag
        if device_type == "Pv" and "reactive_comp_pct" in properties:
            # HR 5040：无功补偿百分比 -1000~1000 表示 -100%~100%，按百分比计算 Q = 额定×pct/100（与功率因数互斥，事件触发二选一）
            raw_pct = int(properties["reactive_comp_pct"])
            raw_pct = raw_pct if raw_pct <= 32767 else raw_pct - 65536
            pct = raw_pct / 10.0  # -100 ~ 100
            nominal_kw = float(
                properties.get("rated_power_kw")
                or properties.get("max_power_kw")
                or properties.get("rated_power")
                or 0
            )
            if nominal_kw > 0 and -100 <= pct <= 100:
                q_kvar = nominal_kw * pct / 100.0
        return p_kw, q_kvar

    def _apply_manual_power_values(self) -> None:
        """
        对手动模式设备，将当前设定写入 topology_data 的 properties。
        """
        if not self.topology_data or not self.device_manual_setpoint:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        for device_id, cfg in self.device_manual_setpoint.items():
            # 只处理当前模式为 manual 的设备
            if self.device_modes.get(device_id) != "manual":
                continue
            device = devices_dict.get(device_id)
            if not device:
                continue
            p_kw = cfg.get("p_kw", 0.0)
            q_kvar = cfg.get("q_kvar", 0.0)
            props = device.setdefault("properties", {})
            props["p_kw"] = p_kw
            props["q_kvar"] = q_kvar

    def _apply_random_power_values(self) -> None:
        """
        对配置为随机模式的设备，在 [min_power, max_power] 内生成新的有功功率（kW）
        并写入 topology_data 的 properties，供本步 _update_network_power_values 使用。
        """
        if not self.topology_data or not self.device_random_config:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        for device_id, cfg in self.device_random_config.items():
            # 只处理当前模式为 random_data 的设备
            if self.device_modes.get(device_id) != "random_data":
                continue
            device = devices_dict.get(device_id)
            if not device:
                continue
            min_p = cfg.get("min_power", 0.0)
            max_p = cfg.get("max_power", 0.0)
            p_kw = min_p + random.random() * (max_p - min_p) if max_p > min_p else min_p
            props = device.setdefault("properties", {})
            props["p_kw"] = p_kw
            props["q_kvar"] = 0.0

    def _apply_historical_power_values(self) -> None:
        """
        历史模式设备：按 playbackIntervalMs 采样间隔从历史数据中读取下一个数据点。
        playbackIntervalMs: 仿真中每隔多少毫秒从历史数据读取并更新一次。
        """
        if not self.topology_data or not self.device_historical_providers:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        
        for device_id, provider in self.device_historical_providers.items():
            if self.device_modes.get(device_id) != "historical_data":
                continue
            device = devices_dict.get(device_id)
            if not device:
                continue
            
            # 获取回放间隔配置（毫秒）
            cfg = self.device_historical_config.get(device_id, {})
            playback_interval_ms = cfg.get("playbackIntervalMs", 1000)
            playback_interval_sec = playback_interval_ms / 1000.0
            
            # 检查是否到达下次采样时间
            last_update = self.device_historical_last_update.get(device_id, 0.0)
            if self.sim_elapsed_seconds - last_update >= playback_interval_sec:
                # 更新索引并读取数据
                current_idx = self.device_historical_index.get(device_id, 0)
                p_kw, q_kvar = provider.get_power_at_index(current_idx)
                
                # 写入设备 properties
                props = device.setdefault("properties", {})
                props["p_kw"] = p_kw
                props["q_kvar"] = q_kvar
                
                # 更新状态
                self.device_historical_index[device_id] = current_idx + 1
                self.device_historical_last_update[device_id] = self.sim_elapsed_seconds
            else:
                # 未到采样时间，保持当前值（不更新）
                pass

    def _flush_pending_commands(self) -> None:
        """
        处理响应延迟 pending 队列：将到期的命令写入设备 properties。
        """
        if not self.device_pending_commands or not self.topology_data:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        now = self.sim_elapsed_seconds
        for device_id in list(self.device_pending_commands.keys()):
            queue = self.device_pending_commands[device_id]
            remaining = []
            for item in queue:
                if item["apply_at"] <= now:
                    device = devices_dict.get(device_id)
                    if device:
                        props = device.setdefault("properties", {})
                        target = item["target_props"]
                        # 互斥逻辑（与 update_device_properties 保持一致）
                        if "power_limit_raw" in target:
                            props.pop("power_limit_pct", None)
                        if "power_limit_pct" in target:
                            props.pop("power_limit_raw", None)
                        if "power_factor" in target:
                            props.pop("reactive_comp_pct", None)
                        if "reactive_comp_pct" in target:
                            props.pop("power_factor", None)
                        props.update(target)
                else:
                    remaining.append(item)
            if remaining:
                self.device_pending_commands[device_id] = remaining
            else:
                del self.device_pending_commands[device_id]

    def _apply_measurement_noise(self) -> None:
        """
        第5阶段：潮流计算后，按设备叠加测量误差到 properties.p_kw / q_kvar。
        误差为 Gaussian 随机扰动，标准差 = |value| * measurementErrorPct / 100。
        这样 Modbus 寄存器和前端元数据都自动带上噪声。
        """
        if not self.device_sim_params or not self.topology_data:
            return
        devices = self.topology_data.get("devices", {})
        if isinstance(devices, list):
            devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
        else:
            devices_dict = devices
        for device_id, params in self.device_sim_params.items():
            error_pct = params.get("measurementErrorPct", 0)
            if error_pct <= 0:
                continue
            device = devices_dict.get(device_id)
            if not device:
                continue
            props = device.get("properties", {})
            p_kw = float(props.get("p_kw", 0.0))
            q_kvar = float(props.get("q_kvar", 0.0))
            sigma_ratio = error_pct / 100.0
            if p_kw != 0:
                props["p_kw"] = p_kw * (1 + random.gauss(0, sigma_ratio))
            if q_kvar != 0:
                props["q_kvar"] = q_kvar * (1 + random.gauss(0, sigma_ratio))

    def _update_network_power_values(self):
        """
        第3阶段：更新网络功率值（纯网络更新）。
        从 properties 读取已过滤的功率值（额定/限制在第2阶段完成，额定容量从拓扑 max_power_kw/rated_power 获取），写入 pandapower 网络。
        """
        if not self.cached_network or not self.topology_data:
            return
        try:
            devices = self.topology_data.get("devices", {})
            if isinstance(devices, list):
                devices_dict = {d.get("id", ""): d for d in devices if d.get("id")}
            else:
                devices_dict = devices
            for device_id, device in devices_dict.items():
                device_type = device.get("device_type", "")
                properties = device.get("properties", {})
                p_kw = 0.0
                if "p_kw" in properties:
                    p_kw = float(properties["p_kw"])
                elif "rated_power" in properties:
                    p_kw = float(properties["rated_power"])
                elif "power" in properties:
                    power_val = properties["power"]
                    if isinstance(power_val, (int, float)):
                        p_kw = float(power_val)
                        if abs(p_kw) > 1000:
                            p_kw = p_kw / 1000.0
                q_kvar = float(properties.get("q_kvar", 0.0))
                # 额定容量与 power_limit_pct 限制已在第2阶段 _apply_modbus_filtering 中完成（从拓扑 max_power_kw/rated_power 获取）
                p_mw = p_kw / 1000.0
                q_mvar = q_kvar / 1000.0
                
                # 根据设备类型更新对应的功率值（有功与无功）
                if device_type == "Pv":
                    # 更新发电机功率（光伏在 pandapower 中为 sgen 表）
                    if device_id in self.cached_device_map.get("generators", {}):
                        gen_idx = self.cached_device_map["generators"][device_id]
                        sgen_df = getattr(self.cached_network, "sgen", None)
                        if sgen_df is not None and 0 <= gen_idx < len(sgen_df):
                            sgen_df.at[gen_idx, "p_mw"] = p_mw
                            if "q_mvar" in sgen_df.columns:
                                sgen_df.at[gen_idx, "q_mvar"] = q_mvar
                
                elif device_type == "Load":
                    # 更新负载功率
                    if device_id in self.cached_device_map.get("loads", {}):
                        load_idx = self.cached_device_map["loads"][device_id]
                        if 0 <= load_idx < len(self.cached_network.load):
                            self.cached_network.load.at[load_idx, "p_mw"] = p_mw
                            if "q_mvar" in self.cached_network.load.columns:
                                self.cached_network.load.at[load_idx, "q_mvar"] = q_mvar
                
                elif device_type == "Storage":
                    # 更新储能功率与并离网（in_service：0=并网参与计算，1=离网不参与）
                    if device_id in self.cached_device_map.get("storages", {}):
                        storage_idx = self.cached_device_map["storages"][device_id]
                        if 0 <= storage_idx < len(self.cached_network.storage):
                            self.cached_network.storage.at[storage_idx, "p_mw"] = p_mw
                            if "q_mvar" in self.cached_network.storage.columns:
                                self.cached_network.storage.at[storage_idx, "q_mvar"] = q_mvar
                            grid_mode = properties.get("grid_mode", 0)
                            in_service = (int(grid_mode) == 0)
                            if "in_service" in self.cached_network.storage.columns:
                                self.cached_network.storage.at[storage_idx, "in_service"] = in_service
                
                elif device_type == "Charger":
                    # 更新充电桩功率（作为负载处理）
                    if device_id in self.cached_device_map.get("loads", {}):
                        load_idx = self.cached_device_map["loads"][device_id]
                        if 0 <= load_idx < len(self.cached_network.load):
                            self.cached_network.load.at[load_idx, "p_mw"] = p_mw
                            if "q_mvar" in self.cached_network.load.columns:
                                self.cached_network.load.at[load_idx, "q_mvar"] = q_mvar
                            
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
        self.device_random_config.clear()
        self.device_modes.clear()
        self.device_manual_setpoint.clear()
        self.device_remote_setpoint.clear()
        self.device_historical_config.clear()
        self.device_historical_providers.clear()
        self.device_historical_index.clear()
        self.device_historical_last_update.clear()
        self.device_sim_params.clear()
        self.device_pending_commands.clear()
        self.sim_elapsed_seconds = 0.0

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
