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
                result = client.read_input_registers(address=0, count=21, device_id=1)
                # voltage_a = client.read_input_registers(address=1, count=1, device_id=1)
                # voltage_b = client.read_input_registers(address=2, count=1, device_id=1)
                # voltage_c = client.read_input_registers(address=3, count=1, device_id=1)
                if not result.isError() and len(result.registers) >= 1:
                    # 组合高低位得到32位无符号整数
                    low_word = result.registers[0]
                    raw_value = low_word
                    if raw_value >= 0x8000:
                        raw_value -= 0x10000
                    
                    # 转换为kW（服务器端已提供kW单位）
                    power_kw = raw_value * 0.5 # 转换为MW再转kW，或直接按kW处理
                    self.meter_data[meter_name]['power'] = power_kw
                    self.meter_data[meter_name]['status'] = 'ok'
                    self.meter_data[meter_name]['voltage_a'] = result.registers[1]
                    self.meter_data[meter_name]['voltage_b'] = result.registers[2]
                    self.meter_data[meter_name]['voltage_c'] = result.registers[3]
                    self.meter_data[meter_name]['current_a'] = result.registers[4]
                    self.meter_data[meter_name]['current_b'] = result.registers[5]
                    self.meter_data[meter_name]['current_c'] = result.registers[6]
                    self.meter_data[meter_name]['active_export'] = result.registers[7]
                    self.meter_data[meter_name]['active_import'] = result.registers[8]
                    self.meter_data[meter_name]['reactive_export'] = result.registers[10]
                    self.meter_data[meter_name]['reactive_import'] = result.registers[11]
                    # 解析无功功率 (16位有符号整数)
                    reactive_raw = result.registers[20]
                    if reactive_raw >= 0x8000:
                        reactive_raw -= 0x10000
                    self.meter_data[meter_name]['reactive_power'] = reactive_raw * 0.5
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
        print(f"[{timestamp}] ")
        
        total_power = 0.0
        active_meters = 0
        
        for i in range(1, self.meter_count + 1):
            meter_name = f"meter_{i}"
            data = self.meter_data[meter_name]
            power = data['power']
            status = data['status']
            voltage_a = data['voltage_a']
            voltage_b = data['voltage_b']
            voltage_c = data['voltage_c']
            current_a = data['current_a']
            current_b = data['current_b']
            current_c = data['current_c']
            active_export = data['active_export']
            active_import = data['active_import']
            reactive_export = data['reactive_export']
            reactive_import = data['reactive_import']
            reactive_power = data['reactive_power']

            if status == 'ok':
                print(
                    f"电表{i}:{power:6.2f}kW | 状态: {status} | Vab:{voltage_a:6.2f}V | Vbc:{voltage_b:6.2f}V | Vca:{voltage_c:6.2f}V | Iab:{current_a:6.2f}A | Ibc:{current_b:6.2f}A | Ica:{current_c:6.2f}A | ActUp:{active_export:6.2f} | ActDown:{active_import:6.2f} | ReactUp:{reactive_export:6.2f} | ReactDown:{reactive_import:6.2f} | Q:{reactive_power:6.2f}"
                )
                total_power += power
                active_meters += 1
            else:
                print(f"电表{i}: 离线   ")
        
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
    
    multi_client = MultiMeterClient(base_port=403, meter_count=1)
    
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
