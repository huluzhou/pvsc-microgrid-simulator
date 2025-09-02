#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modbus服务器管理模块
负责管理电表、储能、光伏、充电桩等设备的Modbus服务器功能
"""

import threading
from bs4 import element
import pandas as pd
from pymodbus.server import StartTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext


class ModbusManager:
    """Modbus服务器管理器"""
    
    def __init__(self, network_model, scene=None):
        self.network_model = network_model
        self.modbus_servers = {}  # 存储服务器实例
        self.modbus_contexts = {}  # 存储Modbus上下文
        self.running_services = set()  # 跟踪运行中的服务
        
        self.ip_devices = []  # 存储具有IP属性的设备列表
        
    def scan_ip_devices(self):
        """扫描网络中具有IP属性的设备"""
        self.ip_devices.clear()
        
        # 扫描静态发电机设备（光伏）
        if hasattr(self.network_model.net, 'sgen') and not self.network_model.net.sgen.empty:
            for idx, row in self.network_model.net.sgen.iterrows():
                if hasattr(row, 'ip') and pd.notna(row.ip) and row.ip:
                    device_info = {
                        'type': 'sgen',
                        'index': idx,
                        'name': row.get('name', f'sgen_{idx}'),
                        'ip': row.ip,
                        'port': row.get('port', 502),  # 默认Modbus端口
                        'p_mw': row.get('p_mw', 0),
                        'q_mvar': row.get('q_mvar', 0)
                    }
                    self.ip_devices.append(device_info)
        
        # 扫描负载设备（包括电表、充电桩）
        if hasattr(self.network_model.net, 'load') and not self.network_model.net.load.empty:
            for idx, row in self.network_model.net.load.iterrows():
                if hasattr(row, 'ip') and pd.notna(row.ip) and row.ip:
                    device_info = {
                        'type': 'load',
                        'index': idx,
                        'name': row.get('name', f'load_{idx}'),
                        'ip': row.ip,
                        'port': row.get('port', 502),
                        'p_mw': row.get('p_mw', 0),
                        'q_mvar': row.get('q_mvar', 0)
                    }
                    self.ip_devices.append(device_info)
        
        # 扫描储能设备
        if hasattr(self.network_model.net, 'storage') and not self.network_model.net.storage.empty:
            for idx, row in self.network_model.net.storage.iterrows():
                if hasattr(row, 'ip') and pd.notna(row.ip) and row.ip:
                    device_info = {
                        'type': 'storage',
                        'index': idx,
                        'name': row.get('name', f'storage_{idx}'),
                        'ip': row.ip,
                        'port': row.get('port', 502),
                        'p_mw': row.get('p_mw', 0),
                        'q_mvar': row.get('q_mvar', 0)
                    }
                    self.ip_devices.append(device_info)
        
        print(f"发现 {len(self.ip_devices)} 个具有IP属性的设备")
        return self.ip_devices
    
    def create_modbus_context(self, device_info):
        """为设备创建Modbus数据上下文"""
        # 创建数据块字典
        store = {
            'di': ModbusSequentialDataBlock(0, [0] * 100),  # 离散输入
            'co': ModbusSequentialDataBlock(0, [0] * 100),  # 线圈
            'hr': ModbusSequentialDataBlock(0, [0] * 100),  # 保持寄存器
            'ir': ModbusSequentialDataBlock(0, [0] * 100)   # 输入寄存器
        }
        
        context = ModbusServerContext(devices=store, single=True)
        return context
    
    def start_modbus_server(self, device_info):
        """为指定设备启动Modbus服务器"""
        device_key = f"{device_info['type']}_{device_info['index']}"

        if device_key in self.modbus_servers or device_key in self.running_services:
            print(f"设备 {device_key} 的Modbus服务器已在运行")
            return False

        try:
            # 创建Modbus上下文
            context = self.create_modbus_context(device_info)
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
                if isinstance(item, MeterItem) and item.properties.get('index') == index:
                    meter_item = item
                    break
            
            if not meter_item:
                print(f"未找到电表图形项: {index}")
                return
                
            # 从电表图形项的properties中获取参数
            element_type = meter_item.properties.get('element_type', 'bus')
            element = meter_item.properties.get('element', 0)
            side = meter_item.properties.get('side', None)
            
            # 获取网络中的实际功率数据
            power_value = 0.0
            
            if element_type == 'load':
                if element in self.network_model.net.load.index:
                    power_value = self.network_model.net.load.loc[element, 'p_mw']
                    
            elif element_type == 'sgen':
                if element in self.network_model.net.sgen.index:
                    power_value = self.network_model.net.sgen.loc[element, 'p_mw']
                    
            elif element_type == 'storage':
                if element in self.network_model.net.storage.index:
                    power_value = self.network_model.net.storage.loc[element, 'p_mw']
                    
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
            power_kw = int(abs(power_value) * 1000)
            
            # 将32位整数拆分为高16位和低16位
            high_word = (power_kw >> 16) & 0xFFFF
            low_word = power_kw & 0xFFFF
            
            # 写入保持寄存器（功能码3，地址4-5）
            slave_context.setValues(3, 4, [high_word, low_word])
            
            # 写入输入寄存器（功能码4，地址4-5）
            slave_context.setValues(4, 4, [high_word, low_word])
            
            # 写入状态寄存器（地址6）
            status = 1 if power_value != 0 else 0
            slave_context.setValues(3, 6, [status])
            slave_context.setValues(4, 6, [status])
            
        except Exception as e:
            print(f"更新电表上下文失败: {e}")
    
    def update_sgen_context(self, device_info, slave_context, **kwargs):
        """更新发电机特定上下文数据"""
        try:
            # 更新发电机状态寄存器 (寄存器地址4-7)
            sn_mva = int(kwargs.get('sn_mva', 0) * 1000)  # 额定容量
            scaling = int(kwargs.get('scaling', 1.0) * 100)  # 比例因子
            
            slave_context.setValues(3, 4, [sn_mva])
            slave_context.setValues(3, 5, [scaling])
            slave_context.setValues(4, 4, [sn_mva])
            slave_context.setValues(4, 5, [scaling])
            
        except Exception as e:
            print(f"更新发电机上下文失败: {e}")
    
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
                        # row = self.network_model.net.meter.loc[device_idx]
                        self.update_meter_context(device_idx, self.modbus_contexts[f"{device_type}_{device_idx}"])
                        
                elif device_type == 'sgen' and hasattr(self.network_model.net, 'sgen'):
                    if device_idx in self.network_model.net.sgen.index:
                        row = self.network_model.net.sgen.loc[device_idx]
                        p_mw = row.get('p_mw', 0)
                        q_mvar = row.get('q_mvar', 0)
                        self.update_sgen_context(device_info, self.modbus_contexts[f"{device_type}_{device_idx}"], p_mw=p_mw, q_mvar=q_mvar)

                elif device_type == 'storage' and hasattr(self.network_model.net, 'storage'):
                    if device_idx in self.network_model.net.storage.index:
                        row = self.network_model.net.storage.loc[device_idx]
                        p_mw = row.get('p_mw', 0)
                        q_mvar = row.get('q_mvar', 0)
                        self.update_storage_context(device_info, self.modbus_contexts[f"{device_type}_{device_idx}"], p_mw=p_mw, q_mvar=q_mvar)
                elif device_type == 'charger' and hasattr(self.network_model.net, 'charger'):
                    if device_idx in self.network_model.net.charger.index:
                        row = self.network_model.net.charger.loc[device_idx]
                        p_mw = row.get('p_mw', 0)
                        q_mvar = row.get('q_mvar', 0)
                        self.update_charger_context(device_info, self.modbus_contexts[f"{device_type}_{device_idx}"], p_mw=p_mw, q_mvar=q_mvar)
                        
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
