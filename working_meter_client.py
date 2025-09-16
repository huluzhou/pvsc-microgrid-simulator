#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作版电表客户端 - 四电表真实测试版
同时连接四个Modbus服务器端口 (403-406)
读取四个电表设备的有功功率值（32位数据，高低位组合）
"""

import time
from pymodbus.client import ModbusTcpClient

class MultiMeterClient:
    """多电表客户端"""
    
    def __init__(self, base_port=403, meter_count=4):
        self.base_port = base_port
        self.meter_count = meter_count
        self.meter_ports = list(range(base_port, base_port + meter_count))
        self.clients = {}
        self.meter_data = {}
        
    def connect_all_meters(self):
        """连接所有电表"""
        print("🔌 连接电表设备...")
        for i, port in enumerate(self.meter_ports):
            try:
                client = ModbusTcpClient(host='127.0.0.1', port=port, timeout=3)
                if client.connect():
                    self.clients[f"meter_{i+1}"] = client
                    self.meter_data[f"meter_{i+1}"] = {
                        'port': port,
                        'power': 0.0,
                        'status': 'connected'
                    }
                    print(f"✅ 电表{i+1} (端口{port}) - 连接成功")
                else:
                    print(f"❌ 电表{i+1} (端口{port}) - 连接失败")
                    return False
            except Exception as e:
                print(f"❌ 电表{i+1} (端口{port}) - 错误: {e}")
                return False
        return True
    
    def read_all_powers(self):
        """读取所有电表的有功功率（32位数据，高低位组合）"""
        for meter_name, client in self.clients.items():
            try:
                # 读取两个连续的16位寄存器（地址0和地址1）
                result = client.read_input_registers(address=0, count=2, device_id=1)
                if not result.isError() and len(result.registers) >= 2:
                    # 组合高低位得到32位无符号整数
                    low_word = result.registers[0]
                    high_word = result.registers[1]
                    raw_value = (high_word << 16) | low_word
                    
                    # 转换为kW（服务器端已提供kW单位）
                    power_kw = raw_value * 0.5 # 转换为MW再转kW，或直接按kW处理
                    self.meter_data[meter_name]['power'] = power_kw
                    self.meter_data[meter_name]['status'] = 'ok'
                else:
                    self.meter_data[meter_name]['status'] = 'read_error'
                    self.meter_data[meter_name]['power'] = 0.0
            except Exception as e:
                self.meter_data[meter_name]['status'] = 'exception'
                self.meter_data[meter_name]['power'] = 0.0
                print(f"⚠️ 电表{meter_name}读取异常: {e}")
    
    def display_powers(self):
        """显示所有电表功率"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] ", end="")
        
        total_power = 0.0
        active_meters = 0
        
        for i in range(1, self.meter_count + 1):
            meter_name = f"meter_{i}"
            data = self.meter_data[meter_name]
            power = data['power']
            status = data['status']
            
            if status == 'ok':
                print(f"电表{i}:{power:6.2f}kW ", end="")
                total_power += power
                active_meters += 1
            else:
                print(f"电表{i}: 离线   ", end="")
        
        print(f"| 总功率:{total_power:7.2f}kW | 在线:{active_meters}/{self.meter_count}")
    
    def close_all(self):
        """关闭所有连接"""
        for client in self.clients.values():
            client.close()
        print("🔌 所有电表连接已关闭")

def main():
    """主函数 - 四电表功率监控"""
    print("🔋 四电表功率监控系统")
    print("=" * 60)
    print("服务器: 127.0.0.1")
    print("端口: 403-406 (四个电表)")
    print("寄存器: 地址0-1 (32位有功功率, 高低位组合)")
    print("-" * 60)
    print("📊 开始监控... 按 Ctrl+C 停止")
    print()
    
    multi_client = MultiMeterClient(base_port=403, meter_count=4)
    
    try:
        if not multi_client.connect_all_meters():
            print("❌ 电表连接失败，请检查服务器是否启动")
            return
            
        count = 0
        while True:
            count += 1
            multi_client.read_all_powers()
            multi_client.display_powers()
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 用户停止监控")
        print(f"📊 总计读取: {count} 次")
    finally:
        multi_client.close_all()

if __name__ == "__main__":
    main()