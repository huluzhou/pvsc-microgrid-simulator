#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
储能客户端 - 多储能真实测试版
同时连接多个Modbus服务器端口 (502)
读取储能设备的输入寄存器数据
"""

import time
from pymodbus.client import ModbusTcpClient

class MultiESSClient:
    """多储能客户端"""

    # 与本项目 Modbus 服务一致：端口 < 1024 时映射到 10000+port（无需 root）
    @staticmethod
    def _bind_port(port: int) -> int:
        return (10000 + port) if port < 1024 else port

    def __init__(self, base_port=502, ess_count=4):
        self.base_port = base_port
        self.ess_count = ess_count
        # 实际连接端口：与模拟器 modbus_server 的映射一致
        self.ess_ports = [self._bind_port(p) for p in range(base_port, base_port + ess_count)]
        self.clients = {}
        self.ess_data = {}
        
    def connect_all_ess(self):
        """连接所有储能设备"""
        print("🔌 连接储能设备...")
        for i, port in enumerate(self.ess_ports):
            try:
                client = ModbusTcpClient(host='127.0.0.1', port=port, timeout=3)
                print(f"🔧 尝试连接储能{i+1} (端口{port})...")
                if client.connect():
                    self.clients[f"ess_{i+1}"] = client
                    self.ess_data[f"ess_{i+1}"] = {
                        'port': port,
                        'active_power': 0.0,
                        'soc': 0.0,
                        'max_charge_power': 0.0,
                        'max_discharge_power': 0.0,
                        'remaining_capacity': 0.0,
                        'rated_capacity': 0.0,
                        'current_a': 0.0,
                        'current_b': 0.0,
                        'current_c': 0.0,
                        'today_charge': 0.0,
                        'today_discharge': 0.0,
                        'total_charge': 0.0,
                        'total_discharge': 0.0,
                        'state1': 0,
                        'state2': 0,
                        'state3': 0,
                        'state4': 0,
                        'available': False,
                        'status': 'connected'
                    }
                    print(f"✅ 储能{i+1} (端口{port}) - 连接成功")
                else:
                    print(f"❌ 储能{i+1} (端口{port}) - 连接失败")
                    return False
            except Exception as e:
                print(f"❌ 储能{i+1} (端口{port}) - 错误: {e}")
                return False
        return True
    
    def read_all_ess_data(self):
        """读取所有储能设备的输入寄存器数据"""
        for ess_name, client in self.clients.items():
            try:
                # 读取所有需要的寄存器数据
                clubSta = client.read_input_registers(address=0, count=1, device_id=1)
                pcs_run = client.read_input_registers(address=408, count=1, device_id=1)
                grid_connected = client.read_input_registers(address=432, count=1, device_id=1)
                syssta = client.read_input_registers(address=839, count=1, device_id=1)#  开关机
                alarm = client.read_input_registers(address=400, count=1, device_id=1)
                soc = client.read_input_registers(address=2, count=1, device_id=1)
                rated_power = client.read_input_registers(address=8, count=2, device_id=1)
                remaining_capacity = client.read_input_registers(address=12, count=1, device_id=1)
                rated_capacity = client.read_input_registers(address=39, count=1, device_id=1)
                current = client.read_input_registers(address=412, count=3, device_id=1)
                active_power = client.read_input_registers(address=420, count=2, device_id=1)
                today_charge = client.read_input_registers(address=426, count=1, device_id=1)
                today_discharge = client.read_input_registers(address=427, count=1, device_id=1)
                total_charge = client.read_input_registers(address=428, count=2, device_id=1)
                total_discharge = client.read_input_registers(address=430, count=2, device_id=1)
                sn = client.read_input_registers(address=900, count=16, device_id=1)  # 读取SN号 (地址900-915)
                charge_status = client.read_holding_registers(address=5033, count=1, device_id=1)  # 充放电状态
                # 写入控制命令 (目前注释掉)
                # client.write_registers(address=4, values=[(-300*10)&0xFFFF], device_id=1)
                # client.write_registers(address=4, values=[0], device_id=1)
                # client.write_registers(address=55, values=[243], device_id=1)
                # client.write_registers(address=5095, values=[0], device_id=1)  # 并网

                # 检查所有寄存器的读取结果
                error_registers = []
                if clubSta.isError():    
                    error_registers.append("状态1(地址0)")
                if pcs_run.isError():
                    error_registers.append("状态2(地址408)")
                if syssta.isError():
                    error_registers.append("状态3(地址839)")
                if alarm.isError():
                    error_registers.append("状态4(地址400)")
                if soc.isError():
                    error_registers.append("SOC(地址2)")
                if rated_power.isError():
                    error_registers.append("额定功率(地址8-9)")
                if remaining_capacity.isError():
                    error_registers.append("剩余容量(地址12)")
                if rated_capacity.isError():
                    error_registers.append("额定容量(地址39)")
                if current.isError():
                    error_registers.append("电流(地址412-414)")
                if active_power.isError():
                    error_registers.append("有功功率(地址420-421)")
                if today_charge.isError():
                    error_registers.append("日充电量(地址426)")
                if today_discharge.isError():
                    error_registers.append("日放电量(地址427)")
                if total_charge.isError():
                    error_registers.append("累计充电量(地址428-429)")
                if total_discharge.isError():
                    error_registers.append("累计放电量(地址430-431)")
                if sn.isError():
                    error_registers.append("SN号(地址900-915)")
                if grid_connected.isError():
                    error_registers.append("并网/离网状态(地址432)")
                
                if not error_registers:
                    data = self.ess_data[ess_name]
                    
                    # 处理状态数据
                    data['state1'] = clubSta.registers[0] if clubSta.registers else 0
                    data['input408'] = pcs_run.registers[0] if pcs_run.registers else 0
                    data['state3'] = syssta.registers[0] if syssta.registers else 0
                    data['state4'] = alarm.registers[0] if alarm.registers else 0
                    data['charge_status'] = charge_status.registers[0] if charge_status.registers else 0
                    
                    # 拼接32位数据并进行单位转换
                    # 有功功率：地址420(低16位) + 地址421(高16位)
                    # 将无符号16位整数转换为有符号16位整数(int16)
                    raw_value = active_power.registers[0]
                    # 如果最高位为1(0x8000)，表示负值，需要减去0x10000
                    active_power_raw = raw_value - 0x10000 if raw_value >= 0x8000 else raw_value
                    data['active_power'] = active_power_raw / 10.0  # 除以10还原实际值 (kW)
                    
                    # 额定功率：地址8(低16位) + 地址9(高16位)
                    max_charge_power_raw = rated_power.registers[0] if rated_power.registers else 0
                    max_discharge_power_raw = rated_power.registers[1] if len(rated_power.registers) > 1 else 0
                    data['max_charge_power'] = max_charge_power_raw / 10.0  # 除以10还原实际值 (kW)
                    data['max_discharge_power'] = max_discharge_power_raw / 10.0  # 除以10还原实际值 (kW)
                    
                    # 电流：ABC三相电流
                    data['current_a'] = current.registers[0] / 10.0 if current.registers else 0.0  # A相电流 (A)
                    data['current_b'] = current.registers[1] / 10.0 if len(current.registers) > 1 else 0.0  # B相电流 (A)
                    data['current_c'] = current.registers[2] / 10.0 if len(current.registers) > 2 else 0.0  # C相电流 (A)
                    
                    # 累计充电量：地址428(低16位) + 地址429(高16位)
                    total_charge_raw = (total_charge.registers[1] << 16) | total_charge.registers[0]
                    data['total_charge'] = total_charge_raw / 10.0  # 除以10还原实际值 (kWh)
                    
                    # 累计放电量：地址430(低16位) + 地址431(高16位)
                    total_discharge_raw = (total_discharge.registers[1] << 16) | total_discharge.registers[0]
                    data['total_discharge'] = total_discharge_raw / 10.0  # 除以10还原实际值 (kWh)
                    
                    # 其他数据转换
                    data['soc'] = soc.registers[0] / 1000.0 * 100.0 if soc.registers else 0.0  # 荷电状态 (%)
                    data['remaining_capacity'] = remaining_capacity.registers[0] / 10.0 if remaining_capacity.registers else 0.0  # 剩余可放电容量 (kWh)
                    data['rated_capacity'] = rated_capacity.registers[0] if rated_capacity.registers else 0.0  # 额定容量 (kWh)
                    data['today_charge'] = today_charge.registers[0] / 10.0 if today_charge.registers else 0.0  # 日充电量 (kWh)
                    data['today_discharge'] = today_discharge.registers[0] / 10.0 if today_discharge.registers else 0.0  # 日放电量 (kWh)
                    
                    # 解析SN号（与PV客户端保持一致的解析逻辑）
                    if sn.registers:
                        sn_str = ''
                        for reg in sn.registers:
                            # 高8位是第一个字符，低8位是第二个字符
                            char1 = chr((reg >> 8) & 0xFF)
                            char2 = chr(reg & 0xFF)
                            sn_str += char1 + char2
                        data['sn'] = sn_str.strip()  # 移除可能的空格
                    else:
                        data['sn'] = ''  # 如果读取失败，设为空字符串
                    
                    # 根据状态4判断设备可用性
                    data['available'] = data['state4'] == 1
                    data['status'] = 'ok'
                    # bit9-并网模式，bit10-离网模式
                    data['grid_connected'] = grid_connected.registers[0] & 0x0200 != 0  # 并网模式为1时表示并网
                else:
                    self.ess_data[ess_name]['status'] = 'read_error'
                    error_msg = ", ".join(error_registers)
                    print(f"⚠️ 储能{ess_name}读取错误: {error_msg}")
            except Exception as e:
                self.ess_data[ess_name]['status'] = 'exception'
                print(f"⚠️ 储能{ess_name}读取异常: {e}")
    
    def display_ess_data(self):
        """显示所有储能设备数据"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}]")
        
        for i in range(1, self.ess_count + 1):
            ess_name = f"ess_{i}"
            data = self.ess_data[ess_name]
            
            if data['status'] == 'ok':
                print(f"  储能{i} (端口{data['port']}):")
                print(f"    {'可用' if data['available'] else '不可用':<12} clubsta: {data['state1']:<3} input408: {data['input408']:<3} syssta: {data['state3']:<3} salarm: {data['state4']:<3}")
                print(f"    荷电状态(SOC): {data['soc']:6.1f}%  剩余容量: {data['remaining_capacity']:6.1f}kWh")
                print(f"    额定容量: {data['rated_capacity']:6.1f}kWh  最大充/放电功率: {data['max_charge_power']:6.1f}/{data['max_discharge_power']:6.1f}kW")
                print(f"    有功功率: {data['active_power']:6.1f}kW  三相电流: {data['current_a']:5.1f}A / {data['current_b']:5.1f}A / {data['current_c']:5.1f}A")
                print(f"    今日充/放电: {data['today_charge']:6.1f}kWh / {data['today_discharge']:6.1f}kWh")
                print(f"    累计充/放电: {data['total_charge']:6.1f}kWh / {data['total_discharge']:6.1f}kWh")
                print(f"    SN号: {data['sn']}")  # 显示SN号
                print(f"    并网状态: {'并网' if data['grid_connected'] else '离网'}")  # 显示并网状态
                print(f"    充放电状态: {'放电' if data['charge_status'] == 1 else '充电' if data['charge_status'] == 2 else '未知'}")  # 显示充放电状态

            elif data['status'] == 'read_error':
                print(f"  储能{i} (端口{data['port']}): 数据读取错误")
            elif data['status'] == 'exception':
                print(f"  储能{i} (端口{data['port']}): 通信异常")
            else:
                print(f"  储能{i} (端口{data['port']}): 离线")
        print("-" * 80)
    
    def close_all(self):
        """关闭所有连接"""
        for client in self.clients.values():
            client.close()
        print("🔌 所有储能设备连接已关闭")

def main():
    """主函数 - 多储能数据监控"""
    base_port = 502
    ess_count = 1
    actual_ports = [MultiESSClient._bind_port(p) for p in range(base_port, base_port + ess_count)]
    print("🔋 多储能数据监控系统")
    print("=" * 60)
    print("服务器: 127.0.0.1")
    print(f"端口: {actual_ports} (与模拟器 Modbus 映射一致，502→10502)")
    print("寄存器: 输入寄存器")
    print("  - 状态1-4: 地址0, 408, 839, 400 (各1个寄存器)")
    print("  - SOC: 地址2 (1个寄存器)")
    print("  - 额定功率: 地址8-9 (2个寄存器)")
    print("  - 剩余容量: 地址12 (1个寄存器)")
    print("  - 额定容量: 地址39 (1个寄存器)")
    print("  - 电流: 地址412-414 (3个寄存器)")
    print("  - 有功功率: 地址420-421 (2个寄存器)")
    print("  - 日充/放电量: 地址426-427 (各1个寄存器)")
    print("  - 累计充/放电量: 地址428-429, 430-431 (各2个寄存器)")
    print("-" * 60)
    print("📊 开始监控... 按 Ctrl+C 停止")
    print()
    
    multi_client = MultiESSClient(base_port=base_port, ess_count=ess_count)
    
    try:
        if not multi_client.connect_all_ess():
            print("❌ 储能设备连接失败，请检查服务器是否启动")
            return
            
        count = 0
        while True:
            count += 1
            multi_client.read_all_ess_data()
            multi_client.display_ess_data()
            time.sleep(3)
            
    except KeyboardInterrupt:
        print(f"\n🛑 用户停止监控")
        print(f"📊 总计读取: {count} 次")
    finally:
        multi_client.close_all()

if __name__ == "__main__":
    main()