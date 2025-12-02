#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
充电桩客户端 - 四充电桩真实测试版
同时连接四个Modbus服务器端口 (702-705)
读取四个充电桩设备的输入寄存器数据
"""

import time
from pymodbus.client import ModbusTcpClient

class MultiChargerClient:
    """多充电桩客户端"""
    
    def __init__(self, base_port=702, charger_count=4):
        self.base_port = base_port
        self.charger_count = charger_count
        self.charger_ports = list(range(base_port, base_port + charger_count))
        self.clients = {}
        self.charger_data = {}
        
    def connect_all_chargers(self):
        """连接所有充电桩"""
        print("🔌 连接充电桩设备...")
        for i, port in enumerate(self.charger_ports):
            try:
                client = ModbusTcpClient(host='127.0.0.1', port=port, timeout=3)
                if client.connect():
                    self.clients[f"charger_{i+1}"] = client
                    self.charger_data[f"charger_{i+1}"] = {
                        'port': port,
                        'active_power': 0.0,
                        'demand_power': 0.0,
                        'rated_power': 0.0,
                        'gun1_status': 0,
                        'gun2_status': 0,
                        'gun3_status': 0,
                        'gun4_status': 0,
                        'status': 'connected'
                    }
                    print(f"✅ 充电桩{i+1} (端口{port}) - 连接成功")
                else:
                    print(f"❌ 充电桩{i+1} (端口{port}) - 连接失败")
                    return False
            except Exception as e:
                print(f"❌ 充电桩{i+1} (端口{port}) - 错误: {e}")
                return False
        return True
    
    def read_all_charger_data(self):
        """读取所有充电桩的输入寄存器数据"""
        for charger_name, client in self.clients.items():
            try:
                # 读取有功功率、需求功率、额定功率 (地址0,2,4)
                power_result = client.read_input_registers(address=0, count=6, device_id=1)
                # 读取枪状态 (地址100-103)
                gun_result = client.read_input_registers(address=100, count=4, device_id=1)
                
                result = client.write_registers(address=0, values=[888], device_id=1)
                if not power_result.isError() and not gun_result.isError():
                # if not power_result.isError():
                    data = self.charger_data[charger_name]
                    
                    # 拼接32位数据并除以10还原实际值
                    # 有功功率：地址0(低16位) + 地址1(高16位)
                    active_power_raw = power_result.registers[0]
                    data['active_power'] = active_power_raw / 10.0  # 除以10还原实际值
                    
                    # 需求功率：地址2(低16位) + 地址3(高16位)  
                    demand_power_raw = power_result.registers[2]
                    data['demand_power'] = demand_power_raw / 10.0  # 除以10还原实际值
                    
                    # 额定功率：地址4(低16位) + 地址5(高16位)
                    rated_power_raw = power_result.registers[4]
                    data['rated_power'] = rated_power_raw # 除以10还原实际值
                    
                    # 枪状态（单16位值）
                    data['gun1_status'] = gun_result.registers[0]  # 枪1状态
                    data['gun2_status'] = gun_result.registers[1]    # 枪2状态  
                    data['gun3_status'] = gun_result.registers[2]    # 枪3状态
                    data['gun4_status'] = gun_result.registers[3]    # 枪4状态
                    data['status'] = 'ok'
                else:
                    self.charger_data[charger_name]['status'] = 'read_error'
            except Exception as e:
                self.charger_data[charger_name]['status'] = 'exception'
                print(f"⚠️ 充电桩{charger_name}读取异常: {e}")
    
    def display_charger_data(self):
        """显示所有充电桩数据"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}]")
        
        for i in range(1, self.charger_count + 1):
            charger_name = f"charger_{i}"
            data = self.charger_data[charger_name]
            
            if data['status'] == 'ok':
                print(f"  充电桩{i} (端口{data['port']}):")
                print(f"    有功功率: {data['active_power']:6.1f}kW")
                print(f"    需求功率: {data['demand_power']:6.1f}kW")
                print(f"    额定功率: {data['rated_power']:6.1f}kW")
                print(f"    枪状态: [1:{data['gun1_status']}] [2:{data['gun2_status']}] [3:{data['gun3_status']}] [4:{data['gun4_status']}]")
            else:
                print(f"  充电桩{i} (端口{data['port']}): 离线")
        print("-" * 60)
    
    def close_all(self):
        """关闭所有连接"""
        for client in self.clients.values():
            client.close()
        print("🔌 所有充电桩连接已关闭")

def main():
    """主函数 - 四充电桩数据监控"""
    print("🔋 四充电桩数据监控系统")
    print("=" * 60)
    print("服务器: 127.0.0.1")
    print("端口: 702-705 (四个充电桩)")
    print("寄存器: 输入寄存器")
    print("  - 有功功率: 地址0-1 (32位，低+高)")
    print("  - 需求功率: 地址2-3 (32位，低+高)")
    print("  - 额定功率: 地址4-5 (32位，低+高)")
    print("  - 枪1状态: 地址6")
    print("  - 枪2状态: 地址7")
    print("  - 枪3状态: 地址8")
    print("  - 枪4状态: 地址9")
    print("-" * 60)
    print("📊 开始监控... 按 Ctrl+C 停止")
    print()
    
    multi_client = MultiChargerClient(base_port=702, charger_count=4)
    
    try:
        if not multi_client.connect_all_chargers():
            print("❌ 充电桩连接失败，请检查服务器是否启动")
            return
            
        count = 0
        while True:
            count += 1
            multi_client.read_all_charger_data()
            multi_client.display_charger_data()
            time.sleep(3)
            
    except KeyboardInterrupt:
        print(f"\n🛑 用户停止监控")
        print(f"📊 总计读取: {count} 次")
    finally:
        multi_client.close_all()

if __name__ == "__main__":
    main()