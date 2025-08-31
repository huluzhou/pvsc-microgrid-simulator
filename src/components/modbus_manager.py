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
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext


class ModbusManager:
    """Modbus服务器管理器"""
    
    def __init__(self, network_model):
        self.network_model = network_model
        self.modbus_servers = {}  # 存储每个设备的Modbus服务器 {device_key: server_info}
        self.modbus_contexts = {}  # 存储每个设备的Modbus上下文 {device_key: context}
        self.modbus_threads = {}  # 存储Modbus服务器线程 {device_key: thread}
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
        # 创建数据块，存储设备的功率数据
        # 地址0-1: 有功功率 (P_MW * 1000，分为高低字节)
        # 地址2-3: 无功功率 (Q_MVAR * 1000，分为高低字节)
        # 地址4: 设备状态 (0=离线, 1=在线)
        # 地址5: 设备类型 (1=负载/电表/充电桩, 2=发电机/光伏, 3=储能)
        
        initial_values = [0] * 20  # 初始化20个寄存器
        
        # 设置设备类型
        if device_info['type'] == 'load':
            initial_values[5] = 1  # 负载/电表/充电桩
        elif device_info['type'] == 'sgen':
            initial_values[5] = 2  # 发电机/光伏
        elif device_info['type'] == 'storage':
            initial_values[5] = 3  # 储能
        
        # 设置设备状态为在线
        initial_values[4] = 1
        
        # 创建数据块字典
        store = {
            'di': ModbusSequentialDataBlock(0, [0] * 100),  # 离散输入
            'co': ModbusSequentialDataBlock(0, [0] * 100),  # 线圈
            'hr': ModbusSequentialDataBlock(0, initial_values + [0] * 80),  # 保持寄存器
            'ir': ModbusSequentialDataBlock(0, initial_values + [0] * 80)   # 输入寄存器
        }
        
        context = ModbusServerContext(devices=store, single=True)
        return context
    
    def start_modbus_server(self, device_info):
        """为指定设备启动Modbus服务器"""
        device_key = f"{device_info['type']}_{device_info['index']}"
        
        if device_key in self.modbus_servers:
            print(f"设备 {device_key} 的Modbus服务器已在运行")
            return
        
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
            
            # 在单独线程中启动服务器
            def run_server():
                try:
                    StartTcpServer(
                        context=context,
                        identity=identity,
                        address=(device_info['ip'], device_info['port']),
                        allow_reuse_address=True
                    )
                except Exception as e:
                    print(f"Modbus服务器启动失败 {device_key}: {e}")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            self.modbus_threads[device_key] = server_thread
            self.modbus_servers[device_key] = {
                'device_info': device_info,
                'context': context,
                'thread': server_thread
            }
            
            print(f"Modbus服务器已启动: {device_info['name']} ({device_info['ip']}:{device_info['port']})")
            
        except Exception as e:
            print(f"启动Modbus服务器失败 {device_key}: {e}")
    
    def update_modbus_data(self, device_info, p_mw, q_mvar):
        """更新设备的Modbus数据"""
        device_key = f"{device_info['type']}_{device_info['index']}"
        
        if device_key not in self.modbus_contexts:
            return
        
        try:
            context = self.modbus_contexts[device_key]
            slave_context = context[0]  # 获取从站上下文
            
            # 将功率值转换为整数 (乘以1000保留3位小数精度)
            p_int = int(p_mw * 1000)
            q_int = int(q_mvar * 1000)
            
            # 将32位整数分解为两个16位寄存器
            p_high = (p_int >> 16) & 0xFFFF
            p_low = p_int & 0xFFFF
            q_high = (q_int >> 16) & 0xFFFF
            q_low = q_int & 0xFFFF
            
            # 更新保持寄存器
            slave_context.setValues(3, 0, [p_high])  # 有功功率高位
            slave_context.setValues(3, 1, [p_low])   # 有功功率低位
            slave_context.setValues(3, 2, [q_high])  # 无功功率高位
            slave_context.setValues(3, 3, [q_low])   # 无功功率低位
            
            # 同时更新输入寄存器
            slave_context.setValues(4, 0, [p_high])
            slave_context.setValues(4, 1, [p_low])
            slave_context.setValues(4, 2, [q_high])
            slave_context.setValues(4, 3, [q_low])
            
        except Exception as e:
            print(f"更新Modbus数据失败 {device_key}: {e}")
    
    def start_all_modbus_servers(self):
        """启动所有具有IP属性设备的Modbus服务器"""
        self.scan_ip_devices()
        
        for device_info in self.ip_devices:
            self.start_modbus_server(device_info)
    
    def stop_all_modbus_servers(self):
        """停止所有Modbus服务器"""
        for device_key in list(self.modbus_servers.keys()):
            try:
                # 注意：pymodbus的StartTcpServer是阻塞的，线程会自然结束
                # 这里我们只是清理引用
                if device_key in self.modbus_threads:
                    del self.modbus_threads[device_key]
                if device_key in self.modbus_contexts:
                    del self.modbus_contexts[device_key]
                if device_key in self.modbus_servers:
                    del self.modbus_servers[device_key]
                    
                print(f"已停止Modbus服务器: {device_key}")
            except Exception as e:
                print(f"停止Modbus服务器失败 {device_key}: {e}")
        
        print("所有Modbus服务器已停止")
    
    def update_all_modbus_data(self):
        """更新所有具有IP属性设备的Modbus数据"""
        for device_info in self.ip_devices:
            try:
                device_type = device_info['type']
                device_idx = device_info['index']
                
                # 从网络模型中获取最新的功率数据
                if device_type == 'load' and hasattr(self.network_model.net, 'load'):
                    if device_idx in self.network_model.net.load.index:
                        row = self.network_model.net.load.loc[device_idx]
                        p_mw = row.get('p_mw', 0)
                        q_mvar = row.get('q_mvar', 0)
                        self.update_modbus_data(device_info, p_mw, q_mvar)
                        
                elif device_type == 'sgen' and hasattr(self.network_model.net, 'sgen'):
                    if device_idx in self.network_model.net.sgen.index:
                        row = self.network_model.net.sgen.loc[device_idx]
                        p_mw = row.get('p_mw', 0)
                        q_mvar = row.get('q_mvar', 0)
                        self.update_modbus_data(device_info, p_mw, q_mvar)
                        
                elif device_type == 'storage' and hasattr(self.network_model.net, 'storage'):
                    if device_idx in self.network_model.net.storage.index:
                        row = self.network_model.net.storage.loc[device_idx]
                        p_mw = row.get('p_mw', 0)
                        q_mvar = row.get('q_mvar', 0)
                        self.update_modbus_data(device_info, p_mw, q_mvar)
                        
            except Exception as e:
                print(f"更新设备Modbus数据失败 {device_info['name']}: {e}")
    
    def get_device_count(self):
        """获取设备数量统计"""
        return {
            'total': len(self.ip_devices),
            'running_servers': len(self.modbus_servers),
            'load_devices': len([d for d in self.ip_devices if d['type'] == 'load']),
            'sgen_devices': len([d for d in self.ip_devices if d['type'] == 'sgen']),
            'storage_devices': len([d for d in self.ip_devices if d['type'] == 'storage'])
        }
    
    def get_device_status(self, device_type, device_idx):
        """获取指定设备的Modbus服务器状态"""
        device_key = f"{device_type}_{device_idx}"
        return device_key in self.modbus_servers