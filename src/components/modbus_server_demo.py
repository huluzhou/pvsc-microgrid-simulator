#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modbus服务器演示程序
演示如何使用ModbusManager类开启和关闭Modbus服务器线程
"""

import time
import sys
import os

# 添加项目根目录到系统路径，确保可以导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.network_model import NetworkModel  # 导入网络模型
from components.modbus_manager import ModbusManager  # 导入Modbus管理器
from components.globals import network_items  # 导入全局网络项


def create_demo_device_info(device_type="meter", index=0, ip="0.0.0.0", port=5020):
    """创建演示用的设备信息字典"""
    return {
        "type": device_type,
        "index": index,
        "name": f"{device_type}_{index}_demo",
        "sn": f"DEMO{device_type.upper()}{index:04d}",  # 示例SN
        "ip": ip,
        "port": port,
        "p_mw": 0.0,
        "q_mvar": 0.0,
        "sn_mva": 1.0,
        "max_e_mwh": 1.0,
    }


def demo_start_stop_single_server():
    """演示启动和停止单个Modbus服务器"""
    print("\n=== 演示启动和停止单个Modbus服务器 ===")
    
    # 创建网络模型实例
    network_model = NetworkModel()
    
    # 创建Modbus管理器实例
    modbus_manager = ModbusManager(network_model)
    
    # 创建演示设备信息
    device_info = create_demo_device_info(device_type="meter", index=1, port=5020)
    print(f"创建演示设备: {device_info['name']} (IP: {device_info['ip']}, Port: {device_info['port']})")
    
    # 启动Modbus服务器
    print(f"启动Modbus服务器...")
    result = modbus_manager.start_modbus_server(device_info)
    if result:
        print(f"服务器启动成功: {device_info['name']}")
        
        # 检查服务器状态
        status = modbus_manager.is_service_running(device_info['type'], device_info['index'])
        print(f"服务器运行状态: {'运行中' if status else '已停止'}")
        
        # 等待一段时间
        print("等待3秒...")
        time.sleep(3)
        
        # 停止Modbus服务器
        print(f"停止Modbus服务器...")
        result = modbus_manager.stop_modbus_server(device_info['type'], device_info['index'])
        
        time.sleep(3)
        if result:
            print(f"服务器停止成功: {device_info['name']}")
            
            # 再次检查服务器状态
            status = modbus_manager.is_service_running(device_info['type'], device_info['index'])
            print(f"服务器运行状态: {'运行中' if status else '已停止'}")
        else:
            print(f"服务器停止失败: {device_info['name']}")
    else:
        print(f"服务器启动失败: {device_info['name']}")


def demo_start_stop_multiple_servers():
    """演示启动和停止多个不同类型的Modbus服务器"""
    print("\n=== 演示启动和停止多个不同类型的Modbus服务器 ===")
    
    # 创建网络模型实例
    network_model = NetworkModel()
    
    # 创建Modbus管理器实例
    modbus_manager = ModbusManager(network_model)
    
    # 创建多个演示设备信息
    device_infos = [
        create_demo_device_info(device_type="meter", index=2, port=5021),
        create_demo_device_info(device_type="static_generator", index=3, port=5022),
        create_demo_device_info(device_type="storage", index=4, port=5023),
        create_demo_device_info(device_type="charger", index=5, port=5024),
    ]
    
    # 启动多个Modbus服务器
    print(f"启动多个Modbus服务器...")
    for device_info in device_infos:
        result = modbus_manager.start_modbus_server(device_info)
        if result:
            print(f"服务器启动成功: {device_info['name']} ({device_info['ip']}:{device_info['port']})")
        else:
            print(f"服务器启动失败: {device_info['name']}")
    
    # 等待一段时间
    print("\n等待3秒...")
    time.sleep(3)
    
    # 停止所有Modbus服务器
    print(f"\n停止所有Modbus服务器...")
    result = modbus_manager.stop_all_modbus_servers()
    
    if result:
        print("所有服务器已停止")
        
        # 检查运行服务数量
        service_count = modbus_manager.get_service_count()
        print(f"当前运行服务数量: {service_count}")
    else:
        print("停止所有服务器失败")


def demo_scan_and_start_all():
    """演示扫描网络设备并启动所有Modbus服务器"""
    print("\n=== 演示扫描网络设备并启动所有Modbus服务器 ===")
    
    # 创建网络模型实例
    network_model = NetworkModel()
    
    # 创建Modbus管理器实例
    modbus_manager = ModbusManager(network_model)
    
    # 扫描网络中的IP设备
    print("扫描网络中的IP设备...")
    devices = modbus_manager.scan_ip_devices()
    
    print(f"发现 {len(devices)} 个具有IP属性的设备")
    
    # 如果没有发现设备，添加一个演示设备
    if not devices:
        print("未发现实际设备，添加一个演示设备")
        modbus_manager.ip_devices.append(create_demo_device_info(port=5025))
    
    # 启动所有Modbus服务器
    print("\n启动所有Modbus服务器...")
    modbus_manager.start_all_modbus_servers()
    
    # 获取设备状态统计
    stats = modbus_manager.get_device_count()
    print(f"\n设备统计信息:")
    print(f"  总设备数: {stats['total']}")
    print(f"  运行中的服务器: {stats['running_servers']}")
    print(f"  运行中的服务: {stats['running_services']}")
    
    # 获取运行中的服务列表
    running_services = modbus_manager.get_running_services()
    print(f"\n运行中的服务列表: {running_services}")
    
    # 等待一段时间
    print("\n等待3秒...")
    time.sleep(3)
    
    # 清理所有Modbus资源
    print("\n清理所有Modbus资源...")
    modbus_manager.cleanup()
    print("清理完成")


def main():
    """主函数"""
    print("==== Modbus服务器管理演示程序 ====")
    print("本程序演示如何使用ModbusManager类开启和关闭Modbus服务器线程")
    
    try:
        # 演示1: 启动和停止单个服务器
        demo_start_stop_single_server()
        
        # # 演示2: 启动和停止多个服务器
        # demo_start_stop_multiple_servers()
        
        # # 演示3: 扫描设备并启动所有服务器
        # demo_scan_and_start_all()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        print("\n演示程序结束")


if __name__ == "__main__":
    main()