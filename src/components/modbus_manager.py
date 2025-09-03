#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modbus服务器管理模块
负责管理电表、储能、光伏、充电桩等设备的Modbus服务器功能
"""

import threading
import pandas as pd
from pymodbus.server import StartTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock, ModbusServerContext, ModbusSparseDataBlock


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
                # 使用本地回环地址127.0.0.1作为默认IP，避免网络配置问题
                if ip and ip != "192.168.1.100":  # 排除无效IP
                    effective_ip = ip
                else:
                    effective_ip = "127.0.0.1"
                    
                device_info = {
                    'type': item.component_type,
                    'index': item.component_index,
                    'name': item.properties.get('name', f"{item.component_type}_{item.component_index}"),
                    'sn': item.properties.get('sn', None),  # 添加SN字段，如果不存在则为None
                    'ip': effective_ip,
                    'port': int(item.properties.get('port', 502)),
                    'p_mw': float(item.properties.get('p_mw', 0)),
                    'q_mvar': float(item.properties.get('q_mvar', 0))
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
        sgen_read_registers = {
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
                ir=ModbusSparseDataBlock(sgen_read_registers)
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
                hr=ModbusSparseDataBlock(meter_registers),
                ir=ModbusSparseDataBlock({})
            )
        }
        
        return ModbusServerContext(devices=device_context, single=False)
    
    def _create_storage_context(self, device_info):
        """创建储能设备专用上下文"""
        # 储能设备寄存器映射
        # SOC: 4 (保持寄存器)
        # 最大容量: 5 (保持寄存器)
        storage_registers = {
            4: 0,  # SOC百分比
            5: 0   # 最大容量
        }
        
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock(storage_registers),
                ir=ModbusSparseDataBlock(storage_registers)
            )
        }
        
        return ModbusServerContext(devices=device_context, single=False)
    
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
        charger_hold_registers = {
            0: 0,  # 有功功率
            2: 0,  # 需求功率
            4: 0,  # 额定功率
        }
        charger_input_registers = {
            100: 0,  # gun1
            101: 0,  # gun2
            102: 0,  # gun3
            103: 0,  # gun4
        }
        
        device_context = {
            1: ModbusDeviceContext(
                di=ModbusSparseDataBlock({}),
                co=ModbusSparseDataBlock({}),
                hr=ModbusSparseDataBlock(charger_registers),
                ir=ModbusSparseDataBlock(charger_registers)
            )
        }
        
        return ModbusServerContext(devices=device_context, single=False)
    
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
        """更新电表特定上下文数据"""
        try:
            # 从场景中获取电表图形项
            from .network_items import MeterItem
            
            # 查找对应的电表图形项
            meter_item = None
            for item in self.scene.items():
                if isinstance(item, MeterItem) and item.component_index == index:
                    meter_item = item
                    break
            
            if not meter_item:
                print(f"未找到电表图形项: {index}")
                return
                
            # 从电表图形项的properties中获取参数
            element_type = meter_item.properties.get('element_type', None)
            element = meter_item.properties.get('element', None)
            side = meter_item.properties.get('side', None)
            
            if not element_type or not element or not side:
                print(f"电表 {index} 缺少必要参数")
                return

            # 获取网络中的实际功率数据
            power_value = 0.0

            if element_type == "load":
                if element in self.network_model.net.load.index:
                    power_value = self.network_model.net.res_load.loc[element, "p_mw"]

            if element_type == "bus":
                if element in self.network_model.net.bus.index:
                    power_value = self.network_model.net.res_bus.loc[element, "p_mw"]

            elif element_type == "sgen":
                if element in self.network_model.net.sgen.index:
                    power_value = self.network_model.net.res_sgen.loc[element, "p_mw"]
                    
            elif element_type == 'storage':
                if element in self.network_model.net.storage.index:
                    power_value = self.network_model.net.res_storage.loc[element, 'p_mw']
                    
            elif element_type == 'line':
                if element in self.network_model.net.line.index:
                    # 获取线路功率，根据side参数确定方向
                    if side == 'from':
                        power_value = self.network_model.net.res_line.loc[element, 'p_from_mw']
                    elif side == 'to':
                        power_value = self.network_model.net.res_line.loc[element, 'p_to_mw']
                    else:
                        # 默认使用from侧功率
                        power_value = self.network_model.net.res_line.loc[element, 'p_from_mw']
                        
            elif element_type == 'trafo':
                if element in self.network_model.net.trafo.index:
                    # 获取变压器功率，根据side参数确定方向
                    if side == 'hv':
                        power_value = self.network_model.net.res_trafo.loc[element, 'p_hv_mw']
                    elif side == 'lv':
                        power_value = self.network_model.net.res_trafo.loc[element, 'p_lv_mw']
                    else:
                        # 默认使用高压侧功率
                        power_value = self.network_model.net.res_trafo.loc[element, 'p_hv_mw']
            
            # 将功率值转换为整数（单位：kW）
            # power_kw = int(abs(power_value) * 1000)
            power_kw = int(power_value / 50 * 100)
            
            # 写入保持寄存器（功能码3，地址0）
            slave_context.setValues(3, 0, [power_kw])
            
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
            
            # 获取光伏图形项
            from .network_items import PVItem
            pv_item = None
            for item in self.scene.items():
                if isinstance(item, PVItem) and item.component_index == index:
                    pv_item = item
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
    
    def update_storage_context(self, device_info, slave_context, **kwargs):
        """更新储能设备特定上下文数据"""
        try:
            # 更新储能状态寄存器 (寄存器地址4-7)
            soc = int(kwargs.get('soc_percent', 0) * 100)  # SOC百分比
            max_e = int(kwargs.get('max_e_mwh', 0) * 1000)  # 最大容量
            
            slave_context.setValues(3, 4, [soc])
            slave_context.setValues(3, 5, [max_e])
            slave_context.setValues(4, 4, [soc])
            slave_context.setValues(4, 5, [max_e])
            
        except Exception as e:
            print(f"更新储能上下文失败: {e}")
    
    def update_charger_context(self, device_info, slave_context, **kwargs):
        """更新充电桩特定上下文数据"""
        try:
            # 更新充电桩状态寄存器 (寄存器地址4-7)
            status = 1 if kwargs.get('in_service', True) else 0
            max_p = int(kwargs.get('max_p_mw', 0) * 1000)  # 最大充电功率
            
            slave_context.setValues(3, 4, [status])
            slave_context.setValues(3, 5, [max_p])
            slave_context.setValues(4, 4, [status])
            slave_context.setValues(4, 5, [max_p])
            
        except Exception as e:
            print(f"更新充电桩上下文失败: {e}")
    
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
                # 由于StartTcpServer内部管理资源，只需清理引用
                server_thread = self.modbus_servers[device_key]
                
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
        """停止所有Modbus服务器"""
        try:
            # 逐个停止每个服务器
            for device_key in list(self.modbus_servers.keys()):
                device_type, device_idx = device_key.rsplit('_', 1)
                self.stop_modbus_server(device_type, int(device_idx))
            
            # 清理所有集合
            self.modbus_servers.clear()
            self.modbus_contexts.clear()
            self.running_services.clear()
            
            print("已停止所有Modbus服务器")
            return True
        except Exception as e:
            print(f"停止所有Modbus服务器失败: {e}")
            return False
    
    def update_all_modbus_data(self):
        """更新所有具有IP属性设备的Modbus数据"""
        for device_info in self.ip_devices:
            try:
                device_type = device_info['type']
                device_idx = device_info['index']
                
                # 从网络模型中获取最新的功率数据
                if device_type == 'meter' and hasattr(self.network_model.net, 'meter'):
                    if device_idx in self.network_model.net.meter.index:
                        self.update_meter_context(device_idx, self.modbus_contexts[f"{device_type}_{device_idx}"])
                        
                elif device_type == 'sgen' and hasattr(self.network_model.net, 'sgen'):
                    if device_idx in self.network_model.net.sgen.index:
                        self.update_sgen_context(device_idx, self.modbus_contexts[f"{device_type}_{device_idx}"])

                elif device_type == 'storage' and hasattr(self.network_model.net, 'storage'):
                    if device_idx in self.network_model.net.storage.index:
                        self.update_storage_context(device_idx, self.modbus_contexts[f"{device_type}_{device_idx}"])

                elif device_type == 'charger' and hasattr(self.network_model.net, 'charger'):
                    if device_idx in self.network_model.net.charger.index:
                        self.update_charger_context(device_idx, self.modbus_contexts[f"{device_type}_{device_idx}"])
                        
            except Exception as e:
                print(f"更新设备Modbus数据失败 {device_info['name']}: {e}")
    
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
