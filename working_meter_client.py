#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作版电表客户端
连接本地Modbus服务器 (127.0.0.1:8002)
读取实时功率数据
"""

import time
import random
from pymodbus.client import ModbusTcpClient

def simulate_power_monitor():
    """模拟功率监控 - 无需真实服务器"""
    print("🔋 电表功率监控 (模拟模式)")
    print("=" * 50)
    print("服务器: 127.0.0.1:8002")
    print("设备ID: 1")
    print("寄存器0: 功率数据 (0.01 kW单位)")
    print("-" * 50)
    print("📊 开始监控... 按 Ctrl+C 停止")
    print()
    
    base_power = 25.0  # 基础功率 25kW
    
    try:
        count = 0
        while True:
            count += 1
            
            # 模拟功率波动
            power_var = random.uniform(-2.5, 2.5)
            current_power = base_power + power_var
            
            # 模拟其他数据
            voltage = 220.0 + random.uniform(-5.0, 5.0)
            current = current_power * 1000 / voltage  # 计算电流
            
            timestamp = time.strftime('%H:%M:%S')
            
            print(f"[{timestamp}] #{count:4d} | "
                  f"功率: {current_power:6.2f} kW | "
                  f"电压: {voltage:5.1f} V | "
                  f"电流: {current:5.2f} A")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 用户停止监控")
        print(f"📊 总计读取: {count} 次")

def test_modbus_connection():
    """测试Modbus连接"""
    print("🔍 测试Modbus连接")
    print("-" * 30)
    
    client = ModbusTcpClient(host='127.0.0.1', port=8001, timeout=3)
    
    try:
        if client.connect():
            print("✅ 连接成功")
            
            while True:
                # 测试读取
                result = client.read_input_registers(address=0, count=1,device_id=1)
                if result.isError():
                    print("❌ 读取失败 - 服务器未配置数据")
                    time.sleep(1)
                    continue
                regs = result.registers
                print(f"📊 读取数据:")
                print(f"  功率: {regs[0]/2} kW")
                # print(f"  电压: {regs[1] * 0.1:.1f} V")
                # print(f"  电流: {regs[2] * 0.01:.2f} A")
                time.sleep(2)
        else:
            print("❌ 连接失败 - 服务器未启动")
            print("💡 使用模拟模式运行")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("💡 使用模拟模式运行")
    finally:
        client.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='电表客户端')
    parser.add_argument('--mode', choices=['test', 'simulate'], default='test',
                       help='运行模式')
    
    args = parser.parse_args()
    
    if args.mode == 'simulate':
        simulate_power_monitor()
    else:
        test_modbus_connection()
        print("\n" + "=" * 50)
        # simulate_power_monitor()