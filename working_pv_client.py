#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
光伏客户端 - 多光伏真实测试版
同时连接多个Modbus服务器端口 (706-709)
读取光伏设备的输入寄存器数据
"""

import time
from pymodbus.client import ModbusTcpClient

class MultiPVClient:
    """多光伏客户端"""
    
    def __init__(self, base_port=602, pv_count=4):
        self.base_port = base_port
        self.pv_count = pv_count
        self.pv_ports = list(range(base_port, base_port + pv_count))
        self.clients = {}
        self.pv_data = {}
        
    def connect_all_pvs(self):
        """连接所有光伏设备"""
        print("🔌 连接光伏设备...")
        for i, port in enumerate(self.pv_ports):
            try:
                client = ModbusTcpClient(host='127.0.0.1', port=port, timeout=3)
                print(f"🔧 尝试连接光伏{i+1} (端口{port})...")
                if client.connect():
                    self.clients[f"pv_{i+1}"] = client
                    self.pv_data[f"pv_{i+1}"] = {
                        'port': port,
                        'active_power': 0.0,
                        'reactive_power': 0.0,
                        'sn': '',
                        'rated_power': 0.0,
                        'today_energy': 0,
                        'total_energy': 0,
                        'reactive_percent_limit': 0,
                        'status': 'connected'
                    }
                    print(f"✅ 光伏{i+1} (端口{port}) - 连接成功")
                else:
                    print(f"❌ 光伏{i+1} (端口{port}) - 连接失败")
                    return False
            except Exception as e:
                print(f"❌ 光伏{i+1} (端口{port}) - 错误: {e}")
                return False
        return True
    
    def read_all_pv_data(self):
        """读取所有光伏设备的输入寄存器数据"""
        for pv_name, client in self.clients.items():
            try:
                test = client.read_input_registers(address=0, count=1, device_id=1)
                # # SN号存储在8个寄存器中(4989-4996)，需要读取所有8个寄存器
                sn = client.read_input_registers(address=4989, count=8, device_id=1)
                rated_power = client.read_input_registers(address=5000, count=1, device_id=1)
                # #电量
                energy_result = client.read_input_registers(address=5002, count=3, device_id=1)
                power_result = client.read_input_registers(address=5030, count=2, device_id=1)
                q_result = client.read_input_registers(address=5032, count=2, device_id=1)
                reactive_percent = client.read_holding_registers(address=5040, count=1, device_id=1)
                
                # client.write_registers(address=5005, values=[1], device_id=1)
                # # client.write_registers(address=5038, values=[400], device_id=1)
                # client.write_registers(address=5007, values=[10], device_id=1)
                # client.write_registers(address=5040, values=[65536-1], device_id=1) #无功百分比
                client.write_registers(address=5040, values=[1], device_id=1) #无功百分比
                # client.write_registers(address=5041, values=[65536-999], device_id=1) # 功率因数

                # 分别检查每个寄存器的读取结果
                error_registers = []
                if not error_registers:
                    data = self.pv_data[pv_name]
                    
                    # 拼接32位数据并进行单位转换
                    # 有功功率：地址0(低16位) + 地址1(高16位)
                    active_power_raw = (power_result.registers[1] << 16) | power_result.registers[0]
                    data['active_power'] = active_power_raw  # 除以10还原实际值 (kW)
                    # 正确解析SN号：每个寄存器包含两个ASCII字符，需要拆分
                    sn_str = ''
                    for reg in sn.registers:
                        # 高8位是第一个字符，低8位是第二个字符
                        char1 = chr((reg >> 8) & 0xFF)
                        char2 = chr(reg & 0xFF)
                        sn_str += char1 + char2
                    data['sn'] = sn_str  # 拼接SN号
                    data['rated_power'] = rated_power.registers[0] / 10.0  # 除以10还原实际值 (kW)
                    data['today_energy'] = energy_result.registers[0] / 10.0  # 除以10还原实际值 (kWh)
                    data['total_energy'] = (energy_result.registers[2]<<16) | energy_result.registers[1]
                    reactive_power_raw = (q_result.registers[1] << 16) | q_result.registers[0]
                    # 转换为32位有符号整数
                    if reactive_power_raw >= 0x80000000:
                        reactive_power_raw -= 0x100000000
                    data['reactive_power'] = reactive_power_raw
                    data['reactive_percent_limit'] = reactive_percent.registers[0]
                    data['status'] = 'ok'
                else:
                    self.pv_data[pv_name]['status'] = 'read_error'
                    error_msg = ", ".join(error_registers)
                    print(f"⚠️ 光伏{pv_name}读取错误: {error_msg}")
            except Exception as e:
                self.pv_data[pv_name]['status'] = 'exception'
                print(f"⚠️ 光伏{pv_name}读取异常: {e}")
    
    def display_pv_data(self):
        """显示所有光伏设备数据"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}]")
        
        for i in range(1, self.pv_count + 1):
            pv_name = f"pv_{i}"
            data = self.pv_data[pv_name]
            
            if data['status'] == 'ok':
                print(f"  光伏{i} (端口{data['port']}):")
                print(f"    SN号: {data['sn']}")
                print(f"    额定功率: {data['rated_power']:6.1f}kW")
                print(f"    有功功率: {data['active_power']:6.1f}KW")
                print(f"    无功功率: {data['reactive_power']:6.1f}kVar")
                print(f"    今日发电量: {data['today_energy']:6.1f}kWh")
                print(f"    总发电量: {data['total_energy']:6.1f}kWh")
                print(f"    无功补偿百分比: {data['reactive_percent_limit']:3d}%")
            else:
                print(f"  光伏{i} (端口{data['port']}): 离线")
        print("-" * 60)
    
    def close_all(self):
        """关闭所有连接"""
        for client in self.clients.values():
            client.close()
        print("🔌 所有光伏设备连接已关闭")

def main():
    """主函数 - 多光伏数据监控"""
    
    multi_client = MultiPVClient(base_port=602, pv_count=3)
    
    try:
        if not multi_client.connect_all_pvs():
            print("❌ 光伏设备连接失败，请检查服务器是否启动")
            return
            
        count = 0
        while True:
            count += 1
            multi_client.read_all_pv_data()
            multi_client.display_pv_data()
            time.sleep(3)
            
    except KeyboardInterrupt:
        print(f"\n🛑 用户停止监控")
        print(f"📊 总计读取: {count} 次")
    finally:
        multi_client.close_all()

if __name__ == "__main__":
    main()
