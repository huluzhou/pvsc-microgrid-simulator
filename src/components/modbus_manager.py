#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modbus服务器管理模块
负责管理电表、储能、光伏、充电桩等设备的Modbus服务器功能
"""

import threading
from pymodbus.server import StartTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSparseDataBlock


class ModbusManager:
    """Modbus服务器管理器"""
    
    def __init__(self, network_model, scene=None):
        self.network_model = network_model
        self.scene = scene  # 存储场景引用
        self.modbus_servers = {}  # 存储服务器实例
        self.modbus_contexts = {}  # 存储Modbus上下文
        self.running_services = set()  # 跟踪运行中的服务
        
        self.ip_devices = []  # 存储具有IP属性的设备列表
        
    def scan_ip_devices(self):
        """扫描网络中具有IP属性的设备"""
        self.ip_devices.clear()
        
        # 从场景中获取所有网络项
        if not hasattr(self, 'scene') or not self.scene:
            print("未找到场景，无法扫描IP设备")
            return self.ip_devices
            
        # 扫描场景中的所有网络项
        for item in self.scene.items():
            if hasattr(item, 'properties') and 'ip' in item.properties and item.properties['ip']:
                ip = item.properties['ip']
                # 使用配置的IP地址，默认为0.0.0.0
                effective_ip = ip if ip else "0.0.0.0"
                    
                device_info = {
                    'type': item.component_type,
                    'index': item.component_index,
                    'name': item.properties.get('name', f"{item.component_type}_{item.component_index}"),
                    'sn': item.properties.get('sn', None),  # 添加SN字段，如果不存在则为None
                    'ip': effective_ip,
                    'port': int(item.properties.get('port', 502)),
                    'p_mw': float(item.properties.get('p_mw', 0)),
                    'q_mvar': float(item.properties.get('q_mvar', 0)),
                    'sn_mva': float(item.properties.get('sn_mva', 0)),
                    'max_e_mwh': float(item.properties.get('max_e_mwh', 1.0)),
                }
                self.ip_devices.append(device_info)
        
        print(f"发现 {len(self.ip_devices)} 个具有IP属性的设备")
        return self.ip_devices
    
    def create_modbus_context(self, device_info):
        """为设备创建Modbus数据上下文（按设备类型定制）"""
        device_type = device_info.get('type')
        
        # 根据设备类型创建定制化的稀疏数据块
        if device_type == 'sgen':
            # 光伏设备专用寄存器映射
            context = self._create_sgen_context(device_info)
        elif device_type == 'meter':
            # 电表设备专用寄存器映射
            context = self._create_meter_context(device_info)
        elif device_type == 'storage':
            # 储能设备专用寄存器映射
            context = self._create_storage_context(device_info)
        elif device_type == 'charger':
            # 充电桩设备专用寄存器映射
            context = self._create_charger_context(device_info)
        else:
            # 默认通用上下文
            context = self._create_default_context(device_info)
        
        return context
    
    def _create_sgen_context(self, device_info):
        """创建光伏设备专用上下文"""
        # 光伏设备寄存器映射
        # SN: 4989-4996 (8个寄存器)
        # 额定功率: 5000
        # 今日发电量: 5002
        # 总发电量: 5003
        # 当前功率: 5030
        sgen_input_registers = {
            4989: 0,  # sn
            4989 + 1: 0,
            4989 + 2: 0,
            4989 + 3: 0,
            4989 + 4: 0,
            4989 + 5: 0,
            4989 + 6: 0,
            4989 + 7: 0,
            5000: 0,  # 额定功率
            5002: 0,  # 今日发电量
            5003: 0,  # 总发电量
            5004: 0,
            5030: 0,  # 当前功率
            5031: 0,
        }
        sgen_hold_registers = {
            5005: 0,  # 开关机
            5038: 0,  # 有功功率限制
            5007: 0,  # 有功功率百分比限制
        }
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock(sgen_hold_registers),
                ir=ModbusSparseDataBlock(sgen_input_registers)
            )
        }
        
        context = ModbusServerContext(devices=device_context, single=False)
        
        # 写入设备SN
        if not self._write_pv_device_sn(context, device_info):
            return None
            
        return context
    
    def _create_meter_context(self, device_info):
        """创建电表设备专用上下文"""
        # 电表设备寄存器映射
        # 当前功率: 0 (保持寄存器)
        meter_registers = {0: 0}
        
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock({}),
                ir=ModbusSparseDataBlock(meter_registers),
            )
        }
        
        return ModbusServerContext(devices=device_context, single=False)
    
    def _create_storage_context(self, device_info):
        """创建储能设备专用上下文"""
        # 储能设备寄存器映射
        storage_input_registers = {
            0: 0,  # state1
            2: 0,  # SOC
            8: 0,  # 额定功率
            9: 0,
            12: 0,  # 剩余可放电容量
            39: 0,  # 额定容量
            40: 0,  # pcs_num
            41: 0,  # battery_cluster_num
            42: 0,  # battery_cluster_capacity
            43: 0,  # battery_cluster_power
            399: 0,  # state4
            408: 0,  # state2
            412: 0,  # A相电流
            413: 0,  # B相电流
            414: 0,  # C相电流
            419: 0,  # 有功功率
            420: 0,
            426: 0,  # 日充电量
            427: 0,  # 日放电量
            428: 0,  # 累计充电总量
            429: 0,
            430: 0,  # 累计放电总量
            431: 0,
            839: 0.0,  # state3
        }
        storage_hold_registers = {
            4: 0,  # 设置功率
            55: 0,  # 开关机
        }
        
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock(storage_hold_registers),
                ir=ModbusSparseDataBlock(storage_input_registers)
            )
        }
        
        context = ModbusServerContext(devices=device_context, single=False)
        
        # 写入储能配置参数
        if not self._write_storage_device_init(context, device_info):
            return None
        self.state = 'halt'   
        return context
        
    def _write_storage_device_init(self, context, device_info):
        """向储能设备的输入寄存器写入配置参数
        
        参数:
            context: Modbus服务器上下文
            device_info: 设备信息字典
            
        返回:
            bool: 成功返回True，失败返回False
        """
        try:
            slave_context = context[1]
            
            # 从设备信息中获取配置参数，使用合理的默认值
            rated_power = int(device_info.get('p_mw', 1.0) * 1000)  # 额定功率 (kW)
            rated_capacity = int(device_info.get('max_e_mwh', 1.0) * 1000)  # 额定容量 (kWh)
            pcs_num = int(device_info.get('pcs_num', 1))  # PCS数量
            battery_cluster_num = int(device_info.get('battery_cluster_num', 2))  # 电池簇数量
            battery_cluster_capacity = int(device_info.get('battery_cluster_capacity', 1000))  # 电池簇容量 (kWh)
            battery_cluster_power = int(device_info.get('battery_cluster_power', 500))  # 电池簇功率 (kW)
            
            # 写入对应的寄存器
            # 额定功率占用两个寄存器 (7-8)，正确的高低16位拆分
            rated_power_value = int(device_info.get('p_mw', 1.0) * 1000 * 10)  # 转换为0.1kW单位
            
            # 将32位值拆分为高低16位
            low_word = rated_power_value & 0xFFFF  # 低16位
            high_word = (rated_power_value >> 16) & 0xFFFF  # 高16位
            
            slave_context.setValues(4, 8, [low_word])   # 额定功率低位
            slave_context.setValues(4, 9, [high_word])  # 额定功率高位
            
            slave_context.setValues(4, 39, [rated_capacity])  # 额定容量
            slave_context.setValues(4, 40, [pcs_num])  # PCS数量
            slave_context.setValues(4, 41, [battery_cluster_num])  # 电池簇数量
            slave_context.setValues(4, 42, [battery_cluster_capacity])  # 电池簇容量
            slave_context.setValues(4, 43, [battery_cluster_power])  # 电池簇功率
            
            print(f"已写入储能设备配置参数: 额定功率={rated_power}kW, 额定容量={rated_capacity}kWh, "
                  f"PCS数量={pcs_num}, 电池簇数量={battery_cluster_num}, "
                  f"电池簇容量={battery_cluster_capacity}kWh, 电池簇功率={battery_cluster_power}kW")
            return True
            
        except Exception as e:
            print(f"写入储能设备配置参数失败: {e}")
            return False
    
    def _create_charger_context(self, device_info):
        """创建充电桩设备专用上下文"""
        # 充电桩设备寄存器映射
        # 有功功率: 0 (保持寄存器)
        # 需求功率: 2 (保持寄存器)
        # 额定功率: 4 (保持寄存器)
        # 枪1状态: 100 (保持寄存器)
        # 枪2状态: 101 (保持寄存器)
        # 枪3状态: 102 (保持寄存器)
        # 枪4状态: 103 (保持寄存器)
        charger_input_registers = {
            0: 0,  # 有功功率
            2: 0,  # 需求功率
            4: 0,  # 额定功率
            100: 1,  # gun1 - 初始状态1
            101: 2,  # gun2 - 初始状态2
            102: 3,  # gun3 - 初始状态3
            103: 4,  # gun4 - 初始状态4
        }
        charger_hold_registers = {
            0:0, #功率限制
        }
        
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock(charger_hold_registers),
                ir=ModbusSparseDataBlock(charger_input_registers)
            )
        }
        context = ModbusServerContext(devices=device_context, single=False)
        
        # 写入额定功率和枪状态信息
        if not self._write_charger_device_init(context, device_info):
            return None

        return context
        
    def _write_charger_device_init(self, context, device_info):
        """向充电桩设备的输入寄存器写入额定功率和枪状态信息
        
        返回:
            bool: 成功返回True，如果设备信息不完整返回False
        """
        try:
            slave_context = context[1]
            
            # 写入额定功率 (单位: kW)
            rated_power = int(device_info.get('sn_mva', 1.0) * 1000)  # 转换为kW
            slave_context.setValues(4, 4, [rated_power])
            
            # 写入枪状态信息 (1, 2, 3, 4)
            slave_context.setValues(4, 100, [1])  # 枪1状态: 1
            slave_context.setValues(4, 101, [2])  # 枪2状态: 2
            slave_context.setValues(4, 102, [3])  # 枪3状态: 3
            slave_context.setValues(4, 103, [4])  # 枪4状态: 4
            
            print(f"已写入充电桩设备额定功率: {rated_power}kW 和枪状态信息 (1,2,3,4)")
            return True
            
        except Exception as e:
            print(f"写入充电桩设备初始化信息失败: {e}")
            return False

    def _create_default_context(self, device_info):
        """创建默认通用上下文"""
        default_registers = {0: 0, 1: 0, 2: 0, 3: 0}
        
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock(default_registers),
                ir=ModbusSparseDataBlock({})
            )
        }
        
        return ModbusServerContext(devices=device_context, single=False)
    
    def _write_pv_device_sn(self, context, device_info):
        """向光伏设备的输入寄存器写入设备SN
        
        返回:
            bool: 成功返回True，如果SN不存在返回False
        """
        try:
            # 检查SN字段是否存在且不为None
            device_sn = device_info.get('sn')
            if device_sn is None or str(device_sn).strip() == '':
                print(f"光伏设备 {device_info['index']} 未设置SN字段，跳过SN写入")
                return False
            
            # 写入输入寄存器4989-4996，使用与给定格式完全相同的逻辑
            slave_context = context[1]
            
            # 按照给定的字符配对逻辑写入寄存器
            slave_context.setValues(4, 4989, [(ord(device_sn[0])) << 8 | ord(device_sn[1])])
            slave_context.setValues(4, 4990, [(ord(device_sn[2])) << 8 | ord(device_sn[3])])
            slave_context.setValues(4, 4991, [(ord(device_sn[4])) << 8 | ord(device_sn[5])])
            slave_context.setValues(4, 4992, [(ord(device_sn[6])) << 8 | ord(device_sn[7])])
            slave_context.setValues(4, 4993, [(ord(device_sn[8])) << 8 | ord(device_sn[9])])
            slave_context.setValues(4, 4994, [(ord(device_sn[10])) << 8 | ord(device_sn[11])])
            slave_context.setValues(4, 4995, [(ord(device_sn[12])) << 8 | ord(device_sn[13])])
            slave_context.setValues(4, 4996, [(ord(device_sn[14])) << 8 | ord(device_sn[15])])
            
            print(f"已写入光伏设备SN到寄存器4989-4996: {device_sn[:16]}")
            
            # 写入额定功率 0.1kva
            rated_power = int(device_info["sn_mva"] * 1000 * 10)
            slave_context.setValues(4, 5000, [rated_power])
            return True
            
        except Exception as e:
            print(f"写入光伏设备SN失败: {e}")
            return False
    
    def start_modbus_server(self, device_info):
        """为指定设备启动Modbus服务器"""
        device_key = f"{device_info['type']}_{device_info['index']}"

        if device_key in self.modbus_servers or device_key in self.running_services:
            print(f"设备 {device_key} 的Modbus服务器已在运行")
            return False

        try:
            # 创建Modbus上下文
            context = self.create_modbus_context(device_info)
            if context is None:
                # 创建失败（SN不存在），直接返回False
                return False
            self.modbus_contexts[device_key] = context
            
            # 创建设备标识
            identity = ModbusDeviceIdentification()
            identity.VendorName = 'PandaPower Simulator'
            identity.ProductCode = 'PPS'
            identity.VendorUrl = 'http://localhost'
            identity.ProductName = f"Device {device_info['name']}"
            identity.ModelName = f"{device_info['type'].upper()} Simulator"
            identity.MajorMinorRevision = '1.0'
            
            # 使用StartTcpServer启动服务器，pymodbus内部管理资源
            server_thread = threading.Thread(
                target=StartTcpServer,
                kwargs={
                    'context': context,
                    'identity': identity,
                    'address': (device_info['ip'], device_info['port'])
                },
                daemon=True
            )
            server_thread.start()
            
            # 记录服务器信息（StartTcpServer内部管理实际服务器实例）
            self.modbus_servers[device_key] = server_thread  # 记录线程引用
            self.running_services.add(device_key)
            
            print(f"已启动Modbus服务器: {device_info['name']} ({device_info['ip']}:{device_info['port']})")
            return True
            
        except OSError as e:
            if e.errno == 10048:  # Windows端口占用错误
                print(f"端口 {device_info['port']} 已被占用，无法启动服务器: {device_key}")
            else:
                print(f"启动Modbus服务器失败 {device_key}: {e}")
            return False
        except Exception as e:
            print(f"启动Modbus服务器失败 {device_key}: {e}")
            self.running_services.discard(device_key)
            if device_key in self.modbus_contexts:
                del self.modbus_contexts[device_key]
            return False

    def update_meter_context(self, index, slave_context):
        """更新电表特定上下文数据 - 优化缓存结构
        
        缓存机制优化：
        - 使用单一缓存结构，减少内存占用
        - 直接按索引存储设备对象，避免重复查找
        - 功率值实时获取，确保数据准确性
        """
        try:
            from .network_items import MeterItem
            
            # 初始化单一缓存结构（如果尚未初始化）
            if not hasattr(self, '_meter_cache'):
                self._meter_cache = {}
            
            # 检查并获取电表设备
            meter_item = self._meter_cache.get(index)
            if meter_item is None:
                # 仅在首次访问时查找设备
                for item in self.scene.items():
                    if isinstance(item, MeterItem) and item.component_index == index:
                        meter_item = item
                        self._meter_cache[index] = meter_item
                        break
            
            if not meter_item:
                print(f"未找到电表图形项: {index}")
                return
            
            # 直接获取映射参数（不缓存，因为访问开销很小）
            element_type = meter_item.properties.get('element_type', None)
            element = meter_item.properties.get('element', None)
            side = meter_item.properties.get('side', None)
            
            
            # 实时获取功率数据（不缓存）
            power_value = 0.0
            try:
                if element_type == "load" and element in self.network_model.net.load.index:
                    power_value = self.network_model.net.res_load.loc[element, "p_mw"]
                elif element_type == "bus" and element in self.network_model.net.bus.index:
                    power_value = self.network_model.net.res_bus.loc[element, "p_mw"]
                elif element_type == "sgen" and element in self.network_model.net.sgen.index:
                    power_value = self.network_model.net.res_sgen.loc[element, "p_mw"]
                elif element_type == 'storage' and element in self.network_model.net.storage.index:
                    power_value = self.network_model.net.res_storage.loc[element, 'p_mw']
                elif element_type == 'line' and element in self.network_model.net.line.index:
                    if side == 'from':
                        power_value = self.network_model.net.res_line.loc[element, 'p_from_mw']
                    elif side == 'to':
                        power_value = self.network_model.net.res_line.loc[element, 'p_to_mw']
                    else:
                        power_value = self.network_model.net.res_line.loc[element, 'p_from_mw']
                elif element_type == 'trafo' and element in self.network_model.net.trafo.index:
                    if side == 'hv':
                        power_value = self.network_model.net.res_trafo.loc[element, 'p_hv_mw']
                    elif side == 'lv':
                        power_value = self.network_model.net.res_trafo.loc[element, 'p_lv_mw']
                    else:
                        power_value = self.network_model.net.res_trafo.loc[element, 'p_hv_mw']
                elif element_type == 'ext_grid' and element in self.network_model.net.ext_grid.index:
                    power_value = self.network_model.net.res_ext_grid.loc[element, 'p_mw']
                        
            except (KeyError, AttributeError):
                power_value = 0.0
            # 转换为kw
            power_kw = int(power_value *1000 / 50 * 100)
            
            # 写入输出寄存器（功能码4，地址0）
            slave_context.setValues(4, 0, [power_kw])
            
        except Exception as e:
            print(f"更新电表上下文失败: {e}")


    def update_sgen_context(self, index, slave_context):
        """更新光伏设备的Modbus寄存器数据
        
        寄存器映射：
        - 5002: 今日发电量 (kWh × 10)
        - 5003-5004: 总发电量 (32位，低16位+高16位)
        - 5030-5031: 当前功率 (32位，低16位+高16位)
        """
        # 寄存器地址常量
        REG_TODAY_ENERGY = 5002
        REG_TOTAL_ENERGY_LOW = 5003
        REG_TOTAL_ENERGY_HIGH = 5004
        REG_POWER_LOW = 5030
        REG_POWER_HIGH = 5031
        INPUT_REG = 4
        MAX_32BIT_UINT = 0xFFFFFFFF

        try:
            # 获取功率数据
            power_mw = self.network_model.net.res_sgen.loc[index, "p_mw"]
            
            # 使用缓存机制提高性能
            from .network_items import PVItem
            if not hasattr(self, '_pv_cache'):
                self._pv_cache = {}
            
            # 检查缓存，如果存在且索引匹配则直接使用
            pv_item = self._pv_cache.get(index)
            if pv_item is None or pv_item.component_index != index:
                # 仅在缓存未命中时遍历场景
                for item in self.scene.items():
                    if isinstance(item, PVItem) and item.component_index == index:
                        pv_item = item
                        self._pv_cache[index] = pv_item
                        break
            
            if pv_item is None:
                raise RuntimeError(f"未找到光伏设备 {index} 的图形项")
            
            # 数据转换和验证
            power_kw = int(round(abs(power_mw) * 1000))  # MW -> kW
            total_energy_wh = int(round(pv_item.total_discharge_energy)) 
            today_energy_wh = int(round(pv_item.today_discharge_energy)) 
            
            # 数据范围检查
            if not (0 <= power_kw <= MAX_32BIT_UINT):
                power_kw = max(0, min(power_kw, MAX_32BIT_UINT))
            
            # 拆分32位数据
            power_low = power_kw & 0xFFFF
            power_high = (power_kw >> 16) & 0xFFFF
            total_low = total_energy_wh & 0xFFFF
            total_high = (total_energy_wh >> 16) & 0xFFFF
            
            # 写入寄存器数据
            slave_context.setValues(INPUT_REG, REG_TODAY_ENERGY, [today_energy_wh * 10 & 0xFFFF])
            slave_context.setValues(INPUT_REG, REG_TOTAL_ENERGY_LOW, [total_low])
            slave_context.setValues(INPUT_REG, REG_TOTAL_ENERGY_HIGH, [total_high])
            slave_context.setValues(INPUT_REG, REG_POWER_LOW, [power_low])
            slave_context.setValues(INPUT_REG, REG_POWER_HIGH, [power_high])
            
        except KeyError as e:
            raise RuntimeError(f"光伏设备数据缺失: {e}")
        except ValueError as e:
            raise RuntimeError(f"数据格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"Modbus寄存器更新失败: {e}")
    
    def update_storage_context(self, index, device_info, slave_context):
        """更新储能设备特定上下文数据"""
        try:
            # 使用缓存机制提高性能 - 通过场景直接查找设备
            from .network_items import StorageItem
            if not hasattr(self, '_storage_cache'):
                self._storage_cache = {}
            
            # 检查缓存，如果存在且索引匹配则直接使用
            storage_item = self._storage_cache.get(index)
            if storage_item is None or storage_item.component_index != index:
                # 仅在缓存未命中时遍历场景
                for item in self.scene.items():
                    if isinstance(item, StorageItem) and item.component_index == index:
                        storage_item = item
                        self._storage_cache[index] = storage_item
                        break
            
            if storage_item is None:
                raise RuntimeError(f"未找到储能设备 {index} 的图形项")
            
            # 从network_item获取实时计算的数据，确保数据范围有效
            soc_percent = max(0.0, min(100.0, storage_item.soc_percent))  # 限制在0-100%
            rated_capacity = max(0.0, device_info.get("max_e_mwh", 1.0))  # 额定容量MWh，确保非负
            active_power = float(self.network_model.net.res_storage.loc[index, "p_mw"])
            
            # 从network_item获取能量统计数据，确保非负
            today_charge_energy = max(0.0, storage_item.today_charge_energy)
            today_discharge_energy = max(0.0, storage_item.today_discharge_energy)
            total_charge_energy = max(0.0, storage_item.total_charge_energy)
            total_discharge_energy = max(0.0, storage_item.total_discharge_energy)
            
            # 更新基础状态寄存器 - 使用合理的16位范围
            soc = max(0, min(100, int(soc_percent)))  # SOC百分比，限制在0-100
            max_e = max(0, min(65535, int(rated_capacity * 1000)))  # 最大容量kWh，限制16位
            
            slave_context.setValues(3, 4, [soc])  # 输入寄存器4: SOC
            slave_context.setValues(3, 5, [max_e])  # 输入寄存器5: 最大容量
            slave_context.setValues(4, 4, [soc])  # 保持寄存器4: SOC
            slave_context.setValues(4, 5, [max_e])  # 保持寄存器5: 最大容量
            
            # 剩余可放电容量 (kWh * 10，保留1位小数)
            remaining_kwh = rated_capacity * (soc_percent / 100.0)
            remaining_capacity = max(0, min(65535, int(remaining_kwh * 10)))
            slave_context.setValues(4, 12, [remaining_capacity])
            
            # 日充电量 (kWh * 10，保留1位小数)
            daily_charge = max(0, min(65535, int(today_charge_energy * 10)))
            slave_context.setValues(4, 426, [daily_charge])
            
            # 日放电量 (kWh * 10，保留1位小数)
            daily_discharge = max(0, min(65535, int(today_discharge_energy * 10)))
            slave_context.setValues(4, 427, [daily_discharge])
            
            # 累计充电量 - 32位无符号整数 (kWh * 10)
            total_charge_wh = int(total_charge_energy * 10)
            total_charge_low = total_charge_wh & 0xFFFF
            total_charge_high = (total_charge_wh >> 16) & 0xFFFF
            slave_context.setValues(4, 428, [total_charge_low])
            slave_context.setValues(4, 429, [total_charge_high])
            
            # 累计放电量 - 32位无符号整数 (kWh * 10)
            total_discharge_wh = int(total_discharge_energy * 10)
            total_discharge_low = total_discharge_wh & 0xFFFF
            total_discharge_high = (total_discharge_wh >> 16) & 0xFFFF
            slave_context.setValues(4, 430, [total_discharge_low])
            slave_context.setValues(4, 431, [total_discharge_high])
            
            # 计算电流 - 修正单相220V计算逻辑
            # 电流(A) = 功率(kW) * 1000 / 电压(V)
            # 转换为0.1A单位：* 10
            if abs(active_power) > 0.001:  # 避免浮点误差
                current_a = abs(active_power) * 1000 / 220.0  # A
                current_value = max(0, min(65535, int(current_a * 10)))  # 0.1A单位
            else:
                current_value = 0
                
            # 三相电流值相同（简化处理）
            slave_context.setValues(4, 412, [current_value])  # A相
            slave_context.setValues(4, 413, [current_value])  # B相
            slave_context.setValues(4, 414, [current_value])  # C相
            
            # 根据功率值自动判断储能设备状态
            if abs(active_power) < 0.001:
                current_state = 'ready'  # 功率接近0，处于就绪状态
            elif active_power > 0:  # 正值为充电
                current_state = 'charge'
            elif active_power < 0:  # 负值为放电
                current_state = 'discharge'
            else:
                current_state = storage_item.state  # 保持原有状态
            
            # 状态映射表
            state_map = {
                'halt': {'reg840': 0, 'reg409': 0, 'reg1': 1},      # 停机
                'ready': {'reg840': 1, 'reg409': 1, 'reg1': 1},     # 就绪
                'charge': {'reg840': 1, 'reg409': 3, 'reg1': 2},    # 充电
                'discharge': {'reg840': 1, 'reg409': 4, 'reg1': 3}, # 放电
                'fault': {'reg840': 1, 'reg409': 2, 'reg1': 4}      # 故障
            }
            
            state_values = state_map.get(current_state, state_map['ready'])
            
            # 设置状态相关寄存器
            slave_context.setValues(4, 840 - 1, [state_values['reg840']])  # 状态寄存器840
            slave_context.setValues(4, 409 - 1, [state_values['reg409']])  # 状态寄存器409
            slave_context.setValues(4, 1 - 1, [state_values['reg1']])      # 状态寄存器1
            
            # 设置可用状态寄存器400
            # 判断设备是否可用：只有在就绪、充电、放电状态时为可用
            if current_state in ['ready', 'charge', 'discharge']:
                slave_context.setValues(4, 400 - 1, [1])  # 可用
            else:
                slave_context.setValues(4, 400 - 1, [0])  # 不可用（停机或故障）
            
            # 调试信息（可选，生产环境可注释掉）
            # if abs(active_power) > 0.001:
            #     print(f"储能设备实时数据已更新: SOC={soc}%, 功率={active_power:.3f}MW, 电流={current_value/10:.1f}A, 状态={current_state}")
            
        except KeyError as e:
            print(f"储能设备数据缺失: {e}")
        except ValueError as e:
            print(f"数据格式错误: {e}")
        except Exception as e:
            print(f"更新储能上下文失败: {e}")
    
    def update_charger_context(self, index, slave_context):
        """更新充电桩设备的Modbus寄存器数据（仅更新有功功率和需求功率）
        
        寄存器映射：
        - 0: 有功功率 (kW) - 实时当前功率
        - 2: 需求功率 (kW) - 最大需求功率
        """
        # 寄存器地址常量
        REG_ACTIVE_POWER = 0
        REG_REQUIRED_POWER = 2
        INPUT_REG = 4  # 使用输入寄存器存储实时数据
        MAX_32BIT_UINT = 0xFFFFFFFF

        try:
            # 获取充电桩功率数据
            power_mw = self.network_model.net.res_load.loc[index, "p_mw"]
            
            # 使用缓存机制提高性能
            from .network_items import ChargerItem
            if not hasattr(self, '_charger_cache'):
                self._charger_cache = {}
            
            # 检查缓存，如果存在且索引匹配则直接使用
            charger_item = self._charger_cache.get(index)
            if charger_item is None or charger_item.component_index != index:
                # 仅在缓存未命中时遍历场景
                for item in self.scene.items():
                    if isinstance(item, ChargerItem) and item.component_index == index:
                        charger_item = item
                        self._charger_cache[index] = charger_item
                        break
            
            if charger_item is None:
                raise RuntimeError(f"未找到充电桩设备 {index} 的图形项")
            
            # 数据转换和验证
            active_power_kw = int(round(abs(power_mw) * 1000*10))  # MW -> kW
            required_power_kw = int(round(charger_item.properties.get('max_p_mw', 50) * 1000*10))  # 最大需求功率
            
            # 数据范围检查
            active_power_kw = max(0, min(active_power_kw, MAX_32BIT_UINT))
            required_power_kw = max(0, min(required_power_kw, MAX_32BIT_UINT))
            
            # 写入寄存器数据（输入寄存器）
            slave_context.setValues(INPUT_REG, REG_ACTIVE_POWER, [active_power_kw])
            slave_context.setValues(INPUT_REG, REG_REQUIRED_POWER, [required_power_kw])
            
        except KeyError as e:
            raise RuntimeError(f"充电桩设备数据缺失: {e}")
        except ValueError as e:
            raise RuntimeError(f"数据格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"Modbus寄存器更新失败: {e}")
    
    def start_all_modbus_servers(self):
        """启动所有具有IP属性设备的Modbus服务器"""
        self.scan_ip_devices()
        
        for device_info in self.ip_devices:
            self.start_modbus_server(device_info)
    
    def stop_modbus_server(self, device_type, device_idx):
        """停止指定设备的Modbus服务器（使用StartTcpServer后简化停止流程）"""
        device_key = f"{device_type}_{device_idx}"
        
        try:
            if device_key in self.modbus_servers:
                # 对于储能设备，停止Modbus服务器时设置状态为poweroff
                if device_type == 'storage':
                    from .network_items import StorageItem
                    # 查找对应的储能设备并设置状态
                    for item in self.scene.items():
                        if isinstance(item, StorageItem) and item.component_index == device_idx:
                            item.state = 'power_off'
                            print(f"储能设备 {device_idx} 已设置为poweroff状态")
                            break
                
                # 由于StartTcpServer内部管理资源，只需清理引用
                self.modbus_servers[device_key]
                
                # 清理上下文和引用
                if device_key in self.modbus_contexts:
                    del self.modbus_contexts[device_key]
                
                if device_key in self.modbus_servers:
                    del self.modbus_servers[device_key]
                
                # 从运行服务集合中移除
                self.running_services.discard(device_key)
                
                print(f"已停止Modbus服务器: {device_key}")
                return True
            else:
                print(f"Modbus服务器未运行: {device_key}")
                return False
        except Exception as e:
            print(f"停止Modbus服务器失败 {device_key}: {e}")
            return False
    
    def stop_all_modbus_servers(self):
        """停止所有Modbus服务器 - 增强内存清理"""
        try:
            # 逐个停止每个服务器
            for device_key in list(self.modbus_servers.keys()):
                device_type, device_idx = device_key.rsplit('_', 1)
                self.stop_modbus_server(device_type, int(device_idx))
            
            # 清理所有集合
            self.modbus_servers.clear()
            self.modbus_contexts.clear()
            self.running_services.clear()
            
            # 清空IP设备列表，避免后续更新尝试
            self.ip_devices.clear()
            
            # 清理所有缓存
            self.clear_device_cache()
            # self.clear_all_members()
            print("已停止所有Modbus服务器")
            return True
        except Exception as e:
            print(f"停止所有Modbus服务器失败: {e}")
            return False

    def clear_all_members(self):
        """清空类中所有成员变量"""
        # 保留基本属性，清空其他所有
        keep_attrs = ['__class__', '__dict__', '__weakref__']
        
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attrs:
                delattr(self, attr)

    def cleanup(self):
        """完整清理Modbus资源"""
        try:
            # 停止所有服务器
            self.stop_all_modbus_servers()
            
            # 清理所有内部引用
            self.modbus_contexts = {}
            self.modbus_servers = {}
            self.running_services = set()
            self.ip_devices = []
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            print("Modbus资源已完全清理")
        except Exception as e:
            print(f"清理Modbus资源时发生错误: {e}")
    
    def update_all_modbus_data(self):
        """更新所有具有IP属性设备的Modbus数据"""
        for device_info in self.ip_devices:
            try:
                device_type = device_info['type']
                device_idx = device_info['index']
                device_key = f"{device_type}_{device_idx}"
                
                # 检查设备服务是否仍在运行
                if device_key not in self.running_services:
                    continue
                    
                # 检查设备上下文是否存在
                if device_key not in self.modbus_contexts:
                    continue
                    
                # 获取正确的slave context
                server_context = self.modbus_contexts[device_key]
                if hasattr(server_context, '__getitem__'):
                    # ModbusServerContext通过[slave_id]访问slave context
                    slave_context = server_context[1]  # 使用slave ID 1
                else:
                    # 如果已经是slave context，直接使用
                    slave_context = server_context
                
                # 从网络模型中获取最新的功率数据
                if device_type == 'meter' and hasattr(self.network_model.net, 'measurement'):
                    if device_idx in self.network_model.net.measurement.index:
                        self.update_meter_context(device_idx, slave_context)
                        
                elif device_type == 'sgen' and hasattr(self.network_model.net, 'sgen'):
                    if device_idx in self.network_model.net.sgen.index:
                        self.update_sgen_context(device_idx, device_info, slave_context)

                elif device_type == 'storage' and hasattr(self.network_model.net, 'storage'):
                    if device_idx in self.network_model.net.storage.index:
                        self.update_storage_context(device_idx, device_info, slave_context)

                elif device_type == 'charger' and hasattr(self.network_model.net, 'load'):  # 充电桩作为负载
                    if device_idx in self.network_model.net.load.index:
                        self.update_charger_context(device_idx, slave_context)
                        
            except Exception as e:
                print(f"更新设备Modbus数据失败 {device_info['name']}: {e}")
    
    def clear_device_cache(self):
        """清除所有设备缓存，在场景变化时调用"""
        if hasattr(self, '_storage_cache'):
            self._storage_cache.clear()
        if hasattr(self, '_meter_cache'):
            self._meter_cache.clear()
        if hasattr(self, '_pv_cache'):
            self._pv_cache.clear()
        if hasattr(self, '_charger_cache'):
            self._charger_cache.clear()
        print("设备缓存已清除")
    
    def get_device_count(self):
        """获取设备数量统计"""
        return {
            'total': len(self.ip_devices),
            'running_servers': len(self.modbus_servers),
            'running_services': len(self.running_services),
            'load_devices': len([d for d in self.ip_devices if d['type'] == 'load']),
            'sgen_devices': len([d for d in self.ip_devices if d['type'] == 'sgen']),
            'storage_devices': len([d for d in self.ip_devices if d['type'] == 'storage'])
        }    
    def get_device_status(self, device_type, device_idx):
        """获取指定设备的Modbus服务器状态"""
        device_key = f"{device_type}_{device_idx}"
        return device_key in self.modbus_servers or device_key in self.running_services
    
    def get_running_services(self):
        """获取当前正在运行的服务列表"""
        return list(self.running_services)
    
    def is_service_running(self, device_type, device_idx):
        """检查指定设备的服务是否正在运行"""
        device_key = f"{device_type}_{device_idx}"
        return device_key in self.running_services
    
    def get_service_count(self):
        """获取运行服务数量"""
        return len(self.running_services)
