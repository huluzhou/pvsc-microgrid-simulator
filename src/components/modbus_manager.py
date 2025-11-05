#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modbus服务器管理模块
负责管理电表、储能、光伏、充电桩等设备的Modbus服务器功能
"""

import threading
from utils.logger import logger
from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSparseDataBlock, ModbusSequentialDataBlock
import asyncio
from pymodbus.server import ModbusTcpServer

class ModbusManager:
    """Modbus服务器管理器"""
    
    def __init__(self, network_model, network_items, power_monitor, scene=None):
        self.network_model = network_model
        self.network_items = network_items
        self.power_monitor = power_monitor
        self.modbus_servers = {}  # 存储服务器实例
        self.modbus_contexts = {}  # 存储Modbus上下文
        self.running_services = set()  # 跟踪运行中的服务
        
        self.ip_devices = []  # 存储具有IP属性的设备列表
        
    def scan_ip_devices(self):
        """扫描网络中具有IP属性的设备"""
        self.ip_devices.clear()

        # 使用全局network_items遍历所有网络项
        for component_type, items_dict in self.network_items.items():
            for component_index, item in items_dict.items():
                if (
                    hasattr(item, "properties")
                    and "ip" in item.properties
                    and item.properties["ip"]
                ):
                    ip = item.properties["ip"]
                    # 使用配置的IP地址，默认为0.0.0.0
                    effective_ip = ip if ip else "0.0.0.0"

                    device_info = {
                        "type": item.component_type,
                        "index": item.component_index,
                        "name": item.properties.get(
                            "name", f"{item.component_type}_{item.component_index}"
                        ),
                        "sn": item.properties.get(
                            "sn", None
                        ),  # 添加SN字段，如果不存在则为None
                        "ip": effective_ip,
                        "port": int(item.properties.get("port", 502)),
                        "p_mw": float(item.properties.get("p_mw", 0)),
                        "q_mvar": float(item.properties.get("q_mvar", 0)),
                        "sn_mva": float(item.properties.get("sn_mva", 0)),
                        "max_e_mwh": float(item.properties.get("max_e_mwh", 1.0)),
                    }
                    self.ip_devices.append(device_info)
        
        logger.info(f"发现 {len(self.ip_devices)} 个具有IP属性的设备")
        return self.ip_devices
    
    def create_modbus_context(self, device_info):
        """为设备创建Modbus数据上下文（按设备类型定制）"""
        device_type = device_info.get('type')
        
        # 根据设备类型创建定制化的稀疏数据块
        if device_type == 'static_generator':
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
        
        # 将寄存器字典转换为列表，用于ModbusSequentialDataBlock
        sgen_input_registers = [0] * 6000
        sgen_input_registers[0+1] = 11
        
        # SN相关寄存器
        sgen_input_registers[4989 + 1] = 0
        sgen_input_registers[4989 + 2] = 0
        sgen_input_registers[4989 + 3] = 0
        sgen_input_registers[4989 + 4] = 0
        sgen_input_registers[4989 + 5] = 0
        sgen_input_registers[4989 + 6] = 0
        sgen_input_registers[4989 + 7] = 0
        sgen_input_registers[4989 + 8] = 0
        
        # 其他重要寄存器
        sgen_input_registers[5000 + 1] = 0  # 额定功率
        sgen_input_registers[5002 + 1] = 0  # 今日发电量
        sgen_input_registers[5003 + 1] = 0  # 总发电量
        sgen_input_registers[5004 + 1] = 0
        sgen_input_registers[5030 + 1] = 0  # 当前功率
        sgen_input_registers[5031 + 1] = 0
        
        # 保持寄存器
        sgen_hold_registers = [0] * 6000
        sgen_hold_registers[5005 + 1] = 1  # 开关机
        sgen_hold_registers[5038 + 1] = 0x7FFF  # 有功功率限制
        sgen_hold_registers[5007 + 1] = 100  # 有功功率百分比限制
        
        # 创建ModbusSequentialDataBlock实例
        holding_regs = ModbusSequentialDataBlock(0, sgen_hold_registers)
        input_regs = ModbusSequentialDataBlock(0, sgen_input_registers)
        
        device_context = {
            1: ModbusDeviceContext(
                hr=holding_regs,
                ir=input_regs
            )
        }
        
        context = ModbusServerContext(devices=device_context, single=False)
        
        # 写入设备SN
        if not self._write_pv_device_sn(context, device_info):
            return None
            
        logger.debug(f"创建光伏设备上下文，SN: {device_info.get('sn', 'N/A')}")
        return context
    
    def _create_meter_context(self, device_info):
        """创建电表设备专用上下文"""
        # 电表设备寄存器映射
        # 当前功率: 0 (保持寄存器)
        meter_input_registers = [0] * 20
        meter_input_registers[0+1] = 0  # 当前功率
        meter_input_registers[1+1] = 220  # 电压A
        meter_input_registers[2+1] = 220  # 电压B
        meter_input_registers[3+1] = 220  # 电压C
        meter_input_registers[4+1] = 65468   # Cur_A A相电流
        meter_input_registers[5+1] = 65469   # Cur_B B相电流
        meter_input_registers[6+1] = 65458   # Cur_C C相电流
        meter_input_registers[7+1] = 1000   # OnGridQ 上网电量
        meter_input_registers[8+1] = 862   # GridPower  下网电量
        meter_input_registers[9+1] = 1000   # MeterActivep  组合有功总电能
        
        # 创建ModbusSequentialDataBlock实例
        input_regs = ModbusSequentialDataBlock(0, meter_input_registers)
        
        device_context = {
            1: ModbusDeviceContext(
                ir=input_regs
            )
        }
        
        return ModbusServerContext(devices=device_context, single=False)
    
    def _create_storage_context(self, device_info):
        """创建储能设备专用上下文"""
        # 储能设备寄存器映射
        storage_hold_registers = [0] * 5100  # 扩大寄存器范围以包含所有需要的寄存器
        storage_hold_registers[4+1] = 0  # 设置功率
        storage_hold_registers[55+1] = 243  # 开关机 默认开机
        storage_hold_registers[5095+1] = 0  # 设置PCS并离网模式：1-离网，0-并网

        # 将storage_input_registers字典转换为长度为1000的列表，用于ModbusSequentialDataBlock
        storage_input_registers = [0] * 1000
        storage_input_registers[0+1] = 3  # state1
        storage_input_registers[2+1] = 288  # SOC
        storage_input_registers[8+1] = 10000  # 最大充电功率
        storage_input_registers[9+1] = 10000  # 最大放电功率
        storage_input_registers[12+1] = 862  # 剩余可放电容量
        storage_input_registers[39+1] = 100  # 额定容量
        storage_input_registers[40+1] = 0  # pcs_num
        storage_input_registers[41+1] = 0  # battery_cluster_num
        storage_input_registers[42+1] = 0  # battery_cluster_capacity
        storage_input_registers[43+1] = 0  # battery_cluster_power
        storage_input_registers[400+1] = 0  # state4
        storage_input_registers[408+1] = 1  # state2
        storage_input_registers[409+1] = 2200  # A相电压
        storage_input_registers[410+1] = 2200  # B相电压
        storage_input_registers[411+1] = 2200  # C相电压
        storage_input_registers[412+1] = 0  # A相电流
        storage_input_registers[413+1] = 0  # B相电流
        storage_input_registers[414+1] = 0  # C相电流
        storage_input_registers[420+1] = 0  # 有功功率
        storage_input_registers[421+1] = 0
        storage_input_registers[426+1] = 0  # 日充电量
        storage_input_registers[427+1] = 0  # 日放电量
        storage_input_registers[428+1] = 0  # 累计充电总量
        storage_input_registers[429+1] = 0
        storage_input_registers[430+1] = 0  # 累计放电总量
        storage_input_registers[431+1] = 0
        storage_input_registers[432+1] = 0  # 当前PCS工作模式：bit9-并网模式，bit10-离网模式
        storage_input_registers[839+1] = 240  # state3 240-停机，243/245-工作正常，242/246-故障

        storage_input_registers[900+1] = 21573 #sn
        storage_input_registers[901+1] = 21313   # SN_902 SN号
        storage_input_registers[902+1] = 21041   # SN_903 SN号
        storage_input_registers[903+1] = 12336   # SN_904 SN号
        storage_input_registers[904+1] = 12851   # SN_905 SN号
        storage_input_registers[905+1] = 12360   # SN_906 SN号
        storage_input_registers[906+1] = 21552   # SN_907 SN号
        storage_input_registers[907+1] = 12355   # SN_908 SN号
        storage_input_registers[908+1] = 20018   # SN_909 SN号
        storage_input_registers[909+1] = 13104   # SN_910 SN号
        storage_input_registers[910+1] = 14641   # SN_911 SN号
        storage_input_registers[911+1] = 13104   # SN_912 SN号
        storage_input_registers[912+1] = 12337   # SN_913 SN号

        holding_regs = ModbusSequentialDataBlock(0, storage_hold_registers)   
        input_regs = ModbusSequentialDataBlock(0, storage_input_registers)
        device_context = {
            1: ModbusDeviceContext(
                hr=holding_regs,
                ir=input_regs
            )
        }
        
        context = ModbusServerContext(devices=device_context, single=False)
        
        # 写入储能配置参数
        if not self._write_storage_device_init(context, device_info):
            return None
        # self.state = 'halt'   
        return context
        
    def _write_storage_device_init(self, context, device_info):
        """向储能设备的输入寄存器写入配置参数
        
        参数:
            context: Modbus服务器上下文
            device_info: 设备信息字典
            
        返回:
            bool: 成功返回True，失败返回False
        """
        try:
            slave_context = context[1]
            
            # 从设备信息中获取配置参数，使用合理的默认值
            rated_power = int(device_info.get('sn_mva', 1.0) * 1000)*10  # 额定功率 (kW)
            rated_capacity = int(device_info.get('max_e_mwh', 1.0) * 1000)# 额定容量 (kWh)
            pcs_num = int(device_info.get('pcs_num', 1))  # PCS数量
            battery_cluster_num = int(device_info.get('battery_cluster_num', 2))  # 电池簇数量
            battery_cluster_capacity = int(device_info.get('battery_cluster_capacity', 1000))  # 电池簇容量 (kWh)
            battery_cluster_power = int(device_info.get('battery_cluster_power', 500))  # 电池簇功率 (kW)
            
            # 确保值在16位寄存器范围内 (0-65535)
            rated_power = max(0, min(65535, rated_power))
            rated_capacity = max(0, min(65535, rated_capacity))
            pcs_num = max(0, min(65535, pcs_num))
            battery_cluster_num = max(0, min(65535, battery_cluster_num))
            battery_cluster_capacity = max(0, min(65535, battery_cluster_capacity))
            battery_cluster_power = max(0, min(65535, battery_cluster_power))
            
            # 写入对应的寄存器
            
            slave_context.setValues(4, 8, [rated_power])   # 额定功率
            slave_context.setValues(4, 9, [rated_power])   # 额定功率
            
            slave_context.setValues(4, 39, [rated_capacity])  # 额定容量
            slave_context.setValues(4, 40, [pcs_num])  # PCS数量
            slave_context.setValues(4, 41, [battery_cluster_num])  # 电池簇数量
            slave_context.setValues(4, 42, [battery_cluster_capacity])  # 电池簇容量
            slave_context.setValues(4, 43, [battery_cluster_power])  # 电池簇功率
            
            # 写入设备SN信息
            device_sn = device_info.get('sn', '')
            if device_sn and str(device_sn).strip() != '':
                for i in range(0, len(device_sn), 2):  # 填入SN
                    if i + 1 < len(device_sn):
                        # 获取当前字符和后一个字符的ASCII码
                        ascii_first = ord(device_sn[i])
                        ascii_second = ord(device_sn[i + 1])
                        combined = (ascii_first << 8) | ascii_second
                        # 写入保持寄存器900开始的地址
                        slave_context.setValues(4, 900 + int(i/2), [combined])
                logger.info(f"已写入储能设备SN到寄存器900开始的地址: {device_sn[:16]}")

            logger.info(f"已写入储能设备配置参数: 额定功率={rated_power}kW, 额定容量={rated_capacity}kWh, "
                  f"PCS数量={pcs_num}, 电池簇数量={battery_cluster_num}, "
                  f"电池簇容量={battery_cluster_capacity}kWh, 电池簇功率={battery_cluster_power}kW")
            return True
            
        except Exception as e:
            logger.error(f"写入储能设备配置参数失败: {e}")
            return False
    
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
        
        # 将寄存器字典转换为列表，用于ModbusSequentialDataBlock
        charger_input_registers = [0] * 200
        charger_input_registers[0 + 1] = 0  # 有功功率
        charger_input_registers[1 + 1] = 1  # 状态
        charger_input_registers[2 + 1] = 0  # 需求功率
        charger_input_registers[3 + 1] = 0  # gun num
        charger_input_registers[4 + 1] = 0  # 额定功率
        charger_input_registers[100 + 1] = 1  # gun1 - 初始状态1
        charger_input_registers[101 + 1] = 2  # gun2 - 初始状态2
        charger_input_registers[102 + 1] = 3  # gun3 - 初始状态3
        charger_input_registers[103 + 1] = 4  # gun4 - 初始状态4
        
        # 保持寄存器
        charger_hold_registers = [0] * 200
        charger_hold_registers[0 + 1] = 0x7FFF  # 功率限制
        
        # 创建ModbusSequentialDataBlock实例
        holding_regs = ModbusSequentialDataBlock(0, charger_hold_registers)
        input_regs = ModbusSequentialDataBlock(0, charger_input_registers)
        
        device_context = {
            1: ModbusDeviceContext(
                hr=holding_regs,
                ir=input_regs
            )
        }
        context = ModbusServerContext(devices=device_context, single=False)
        
        # 写入额定功率和枪状态信息
        if not self._write_charger_device_init(context, device_info):
            return None

        return context
        
    def _write_charger_device_init(self, context, device_info):
        """向充电桩设备的输入寄存器写入额定功率和枪状态信息
        
        返回:
            bool: 成功返回True，如果设备信息不完整返回False
        """
        try:
            slave_context = context[1]
            
            # 写入额定功率 (单位: kW，32位无符号整数)
            rated_power = int(device_info.get('sn_mva', 1.0) * 1000)  # 转换为kW
            
            # 分高低位写入（地址4:低16位 + 地址5:高16位）
            rated_power_low = rated_power & 0xFFFF
            slave_context.setValues(4, 4, [rated_power_low])
            
            # 写入枪状态信息 (1, 2, 3, 4)
            slave_context.setValues(4, 100, [1])  # 枪1状态: 1
            slave_context.setValues(4, 101, [2])  # 枪2状态: 2
            slave_context.setValues(4, 102, [3])  # 枪3状态: 3
            slave_context.setValues(4, 103, [4])  # 枪4状态: 4
            
            logger.info(f"已写入充电桩设备额定功率: {rated_power}kW 和枪状态信息 (1,2,3,4)")
            return True
            
        except Exception as e:
            logger.error(f"写入充电桩设备初始化信息失败: {e}")
            return False

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
                logger.warning(f"光伏设备 {device_info['index']} 未设置SN字段，跳过SN写入")
                return False
            
            # 写入输入寄存器4989-4996，使用与给定格式完全相同的逻辑
            slave_context = context[1]
            
            # 按照给定的字符配对逻辑写入寄存器
            # FIXME:只支持16个字符
            slave_context.setValues(4, 4989, [(ord(device_sn[0])) << 8 | ord(device_sn[1])])
            slave_context.setValues(4, 4990, [(ord(device_sn[2])) << 8 | ord(device_sn[3])])
            slave_context.setValues(4, 4991, [(ord(device_sn[4])) << 8 | ord(device_sn[5])])
            slave_context.setValues(4, 4992, [(ord(device_sn[6])) << 8 | ord(device_sn[7])])
            slave_context.setValues(4, 4993, [(ord(device_sn[8])) << 8 | ord(device_sn[9])])
            slave_context.setValues(4, 4994, [(ord(device_sn[10])) << 8 | ord(device_sn[11])])
            slave_context.setValues(4, 4995, [(ord(device_sn[12])) << 8 | ord(device_sn[13])])
            slave_context.setValues(4, 4996, [(ord(device_sn[14])) << 8 | ord(device_sn[15])])
            
            logger.info(f"已写入光伏设备SN到寄存器4989-4996: {device_sn[:16]}")
            
            # 写入额定功率 0.1kva
            rated_power = int(device_info["sn_mva"] * 1000 * 10)
            slave_context.setValues(4, 5000, [rated_power])
            return True
            
        except Exception as e:
            logger.error(f"写入光伏设备SN失败: {e}")
            return False
    def start_modbus_server(self, device_info):
        """启动Modbus TCP服务器（使用底层ModbusTcpServer类）"""
        device_key = f"{device_info['type']}_{device_info['index']}"

        if device_key in self.modbus_servers or device_key in self.running_services:
            logger.warning(f"设备 {device_key} 的Modbus服务器已在运行")
            return False

        try:
            # 1. 创建Modbus上下文（数据存储）
            context = self.create_modbus_context(device_info)  # 复用你的上下文创建逻辑
            if not context:
                return False
            self.modbus_contexts[device_key] = context

            # 2. 创建设备标识
            identity = ModbusDeviceIdentification()
            identity.VendorName = 'PandaPower Simulator'
            identity.ProductCode = 'PPS'
            identity.ProductName = f"Device {device_info['name']}"
            identity.ModelName = f"{device_info['type'].upper()} Simulator"
            identity.MajorMinorRevision = '1.0'

            # 4. 在独立线程中启动服务器（避免阻塞主线程）
            # 为了避免线程间共享异步对象导致的问题，我们需要特殊的处理方式
            # 我们先创建一个事件，用于在线程内部创建服务器实例后通知主线程
            server_ready_event = threading.Event()
            thread_server = [None]  # 使用列表作为可变容器来存储服务器引用
            
            # 线程函数：运行异步服务器的事件循环
            def run_server():
                # 在新线程中创建并设置事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # 在事件循环中创建并启动服务器
                async def start_server():
                    # 在异步函数内部创建服务器
                    server = ModbusTcpServer(
                        context=context,
                        identity=identity,
                        address=(device_info['ip'], device_info['port'])
                    )
                    
                    # 存储服务器引用，以便主线程可以访问
                    thread_server[0] = server
                    
                    # 通知主线程服务器已创建
                    server_ready_event.set()
                    
                    # 启动服务器
                    await server.serve_forever()
                
                # 在事件循环中运行异步函数
                loop.run_until_complete(start_server())
                loop.close()

            # 创建并启动线程
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            # 等待服务器实例在线程中创建完成（最多等待2秒）
            server_ready_event.wait(timeout=2.0)
            
            # 获取服务器实例
            server = thread_server[0]
            if server is None:
                logger.error(f"服务器实例创建失败: {device_key}")
                server_thread.join(timeout=1.0)  # 尝试等待线程结束
                return False

            # 5. 保存服务器实例和线程引用
            self.modbus_servers[device_key] = {
                "server": server,       # 异步服务器实例
                "thread": server_thread # 运行服务器的线程
            }
            self.running_services.add(device_key)

            logger.info(f"已启动Modbus服务器: {device_info['name']} ({device_info['ip']}:{device_info['port']}) ")
            return True

        except OSError as e:
            if e.errno == 10048:
                logger.warning(f"端口 {device_info['port']} 已被占用: {device_key}")
            else:
                logger.error(f"启动失败 {device_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"启动失败 {device_key}: {e}")
            self.running_services.discard(device_key)
            if device_key in self.modbus_contexts:
                del self.modbus_contexts[device_key]
            return False

    def stop_modbus_server(self, device_type, device_idx):
        """关闭Modbus服务器并终止线程"""
        device_key = f"{device_type}_{device_idx}"
        if device_key not in self.modbus_servers or device_key not in self.running_services:
            logger.warning(f"设备 {device_key} 未运行")
            return False

        try:
            # 1. 获取服务器实例和线程
            server_data = self.modbus_servers[device_key]
            server = server_data["server"]
            server_thread = server_data["thread"]

            # 2. 停止异步服务器（核心：调用服务器的stop方法）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.shutdown())  # 优雅关闭服务器
            loop.close()

            # 3. 等待线程结束（最多等待5秒）
            server_thread.join(timeout=5.0)
            if server_thread.is_alive():
                logger.warning(f"服务器线程 {device_key} 未正常退出")
            else:
                logger.info(f"服务器线程 {device_key} 已终止")

            # 4. 清理资源
            self.running_services.discard(device_key)
            del self.modbus_servers[device_key]
            if device_key in self.modbus_contexts:
                del self.modbus_contexts[device_key]

            return True

        except Exception as e:
            logger.error(f"关闭服务器失败 {device_key}: {e}")
            return False

    def update_meter_context(self, index, slave_context):
        """更新电表特定上下文数据 - 优化缓存结构
        
        缓存机制优化：
        - 使用单一缓存结构，减少内存占用
        - 直接按索引存储设备对象，避免重复查找
        - 功率值实时获取，确保数据准确性
        
        寄存器映射：
        - 地址0: 有功功率 (16位)
        - 地址1: A相电压 (16位)
        - 地址2: B相电压 (16位)
        - 地址3: C相电压 (16位)
        """
        try:
            # 获取有功功率值
            power_value = self.power_monitor.get_meter_measurement(index, 'active_power')
            power_kw = int(power_value * 1000 / 50 * 100) & 0xFFFF
            
            # 写入地址0：有功功率（16位）
            slave_context.setValues(4, 0, [power_kw])
            
            # 获取电压值（假设三相电压相同，实际应用中可能需要分别获取）
            voltage_value = self.power_monitor.get_meter_measurement(index, 'voltage')
            # 电压值转换为整数格式（kV转换为V）
            voltage_v = int(voltage_value * 1000) & 0xFFFF
            
            # 写入地址1：A相电压（16位）
            slave_context.setValues(4, 1, [voltage_v])
            
            # 写入地址2：B相电压（16位）
            # 这里暂时使用与A相相同的电压值，实际应用中可能需要分别获取
            slave_context.setValues(4, 2, [voltage_v])
            
            # 写入地址3：C相电压（16位）
            # 这里暂时使用与A相相同的电压值，实际应用中可能需要分别获取
            slave_context.setValues(4, 3, [voltage_v])

        except Exception as e:
            logger.error(f"更新电表上下文失败: {e}")


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
            power_mw = self.network_model.net.res_sgen.at[index, "p_mw"]
            
            # 使用缓存机制提高性能
            # 直接使用network_items[component_type][component_index]查找光伏设备
            if 'static_generator' in self.network_items and index in self.network_items['static_generator']:
                pv_item = self.network_items['static_generator'][index]
            
            if pv_item is None:
                raise RuntimeError(f"未找到光伏设备 {index} 的图形项")
            
            # 数据转换和验证
            power_w = int(round(abs(power_mw) * 1000 * 1000))  # MW -> kW -> W
            total_energy_wh = int(round(pv_item.total_discharge_energy)) 
            today_energy_wh = int(round(pv_item.today_discharge_energy)) 
            
            # 数据范围检查
            if not (0 <= power_w <= MAX_32BIT_UINT):
                logger.warning(f"光伏设备 {index} 功率超出范围: {power_w} W")
                power_w = max(0, min(power_w, MAX_32BIT_UINT))
            
            # 拆分32位数据
            power_low = power_w & 0xFFFF
            power_high = (power_w >> 16) & 0xFFFF
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
    
    def update_storage_context(self, index, device_info, slave_context):
        """更新储能设备特定上下文数据"""
        try:
            # 直接使用network_items[component_type][component_index]查找储能设备
            if 'storage' in self.network_items and index in self.network_items['storage']:
                storage_item = self.network_items['storage'][index]
            
            if storage_item is None:
                raise RuntimeError(f"未找到储能设备 {index} 的图形项")

            # 从network_item获取实时计算的数据，确保数据范围有效
            soc = max(0, min(1000, int(storage_item.soc_percent * 1000)))  # SOC百分比，限制在0-100
            # 
            rated_capacity = max(
                0.0, storage_item.properties.get("max_e_mwh", 1.0)
            )  # 额定容量MWh，确保非负
            remaining_kwh = rated_capacity * storage_item.soc_percent *1000
            remaining_capacity = max(0, min(65535, int(remaining_kwh * 10)))
            #
            active_power_raw = float(
                -self.network_model.net.res_storage.at[index, "p_mw"]
            )
            active_power = int(active_power_raw * 1000 * 10)
            # 计算电流 - 修正单相220V计算逻辑
            # 电流(A) = 功率(kW) * 1000 / 电压(V)
            # 转换为0.1A单位：* 10
            if abs(active_power_raw) > 0.001:  # 避免浮点误差
                current_a = abs(active_power_raw) * 1000 / 220.0  # A
                current_value = max(0, min(65535, int(current_a * 10)))  # 0.1A单位
            else:
                current_value = 0
            # 从network_item获取能量统计数据，确保非负
            today_charge_energy = max(0.0, storage_item.today_charge_energy)
            today_discharge_energy = max(0.0, storage_item.today_discharge_energy)
            total_charge_energy = max(0.0, storage_item.total_charge_energy)
            total_discharge_energy = max(0.0, storage_item.total_discharge_energy)

            # 剩余可放电容量 (kWh * 10，保留1位小数)
            # 日充电量 (kWh * 10，保留1位小数)
            daily_charge = max(0, min(65535, int(today_charge_energy * 10)))
            # 日放电量 (kWh * 10，保留1位小数)
            daily_discharge = max(0, min(65535, int(today_discharge_energy * 10)))
            # 累计充电量 - 32位无符号整数 (kWh * 10)
            total_charge_wh = int(total_charge_energy * 10)
            total_charge_low = total_charge_wh & 0xFFFF
            total_charge_high = (total_charge_wh >> 16) & 0xFFFF
            # 累计放电量 - 32位无符号整数 (kWh * 10)
            total_discharge_wh = int(total_discharge_energy * 10)
            total_discharge_low = total_discharge_wh & 0xFFFF
            total_discharge_high = (total_discharge_wh >> 16) & 0xFFFF

            current_state = storage_item.state  # 保持原有状态

            # 状态映射表
            state_map = {
                "halt": {"reg840": 240, "reg409": 0, "reg1": 1},  # 停机
                "ready": {"reg840": 243, "reg409": 1, "reg1": 1},  # 就绪
                "charge": {"reg840": 245, "reg409": 3, "reg1": 2},  # 充电
                "discharge": {"reg840": 245, "reg409": 4, "reg1": 3},  # 放电
                "fault": {"reg840": 242, "reg409": 2, "reg1": 4},  # 故障
            }

            state_values = state_map.get(current_state, state_map['ready'])
            slave_context.setValues(4, 2, [soc])  # 输入寄存器4: SOC
            slave_context.setValues(4, 12, [remaining_capacity])
            # 三相电流值相同（简化处理）
            slave_context.setValues(4, 412, [current_value])  # A相
            slave_context.setValues(4, 413, [current_value])  # B相
            slave_context.setValues(4, 414, [current_value])  # C相
            slave_context.setValues(4, 419, [active_power&0xFFFF])  #视在功率
            slave_context.setValues(4, 420, [active_power&0xFFFF])  #有功功率
            slave_context.setValues(4, 426, [daily_charge])
            slave_context.setValues(4, 427, [daily_discharge])
            slave_context.setValues(4, 428, [total_charge_low])
            slave_context.setValues(4, 429, [total_charge_high])
            slave_context.setValues(4, 430, [total_discharge_low])
            slave_context.setValues(4, 431, [total_discharge_high])
            # 设置状态相关寄存器
            slave_context.setValues(4, 839, [state_values['reg840']])  # 状态寄存器840
            slave_context.setValues(4, 408, [state_values['reg409']])  # 状态寄存器409
            slave_context.setValues(4, 0, [state_values['reg1']])      # 状态寄存器1
            # 设置可用状态寄存器400
            # 判断设备是否可用：只有在就绪、充电、放电状态时为可用
            if current_state in ['ready', 'charge', 'discharge','halt']:
                slave_context.setValues(4, 400, [1])  # 可用
                alarm_401 = 1
            else:
                slave_context.setValues(4, 400, [0])  # 不可用（停机或故障）
                alarm_401 = 0
            
            logger.info(f"储能设备 {index} 状态更新: {current_state}")
            logger.info(f"电池柜状态:{state_values['reg1']},工作状态:{state_values['reg409']},开关机状态:{state_values['reg840']},警报状态:{alarm_401}")
            # 调试信息（可选，生产环境可注释掉）
            # if abs(active_power) > 0.001:
            #     logger.debug(f"储能设备实时数据已更新: SOC={soc}%, 功率={active_power:.3f}MW, 电流={current_value/10:.1f}A, 状态={current_state}")
            
            # 更新并网/离网状态到保持寄存器5044
            # 从storage_item获取grid_connected属性，确保正确处理各种情况
            try:
                grid_connected = getattr(storage_item, 'grid_connected', True)
                # 确保grid_connected是布尔值，避免None或0值导致的问题
                grid_connected = bool(grid_connected)
                # 根据grid_connected值设置对应的位标志
                # 当为true时，设置bit9为并网模式；当为false时，设置bit10为离网模式
                if grid_connected:
                    # bit9设置为1（2^9=512）
                    mode_value = 512  # 2^9 = 512 (bit9)
                    mode_text = "并网"
                else:
                    # bit10设置为1（2^10=1024）
                    mode_value = 1024  # 2^10 = 1024 (bit10)
                    mode_text = "离网"
                logger.info(f"储能设备 {index} 并网/离网状态更新: {mode_text}模式, grid_connected值: {grid_connected}")
            except Exception as e:
                # 发生异常时默认设置为并网模式
                logger.error(f"获取储能设备 {index} 并网状态时出错: {e}")
                mode_value = 512  # 默认设置为并网模式
                mode_text = "并网(默认)"
            # 写入输入寄存器432表示当前PCS工作模式
            slave_context.setValues(4, 432, [mode_value])
            logger.info(f"储能设备 {index} 并网/离网状态更新: {mode_text}模式")
            
        except KeyError as e:
            logger.error(f"储能设备数据缺失: {e}")
        except ValueError as e:
            logger.error(f"数据格式错误: {e}")
        except Exception as e:
            logger.error(f"更新储能上下文失败: {e}")
    
    def update_charger_context(self, index, slave_context):
        """更新充电桩设备的Modbus寄存器数据（仅更新有功功率和需求功率）
        
        寄存器映射：
        - 0: 有功功率 (kW) - 实时当前功率
        - 2: 需求功率 (kW) - 最大需求功率
        """
        # 寄存器地址常量
        REG_ACTIVE_POWER = 0
        REG_REQUIRED_POWER = 2
        INPUT_REG = 4  # 使用输入寄存器存储实时数据
        MAX_16BIT_UINT = 0xFFFF

        try:
            # 获取充电桩功率数据
            power_mw = self.network_model.net.res_load.at[index, "p_mw"]
            
            # 直接使用network_items[component_type][component_index]查找充电桩设备
            if 'charger' in self.network_items and index in self.network_items['charger']:
                charger_item = self.network_items['charger'][index]
            
            if charger_item is None:
                raise RuntimeError(f"未找到充电桩设备 {index} 的图形项")
            
            # 数据转换和验证
            active_power_kw = int(round(abs(power_mw) * 1000*10))  # MW -> kW
            required_power_kw = int(round(charger_item.required_power * 1000 *10))  # 最大需求功率
            

            # 数据范围检查
            active_power_kw = max(0, min(active_power_kw, MAX_16BIT_UINT))
            required_power_kw = max(0, min(required_power_kw, MAX_16BIT_UINT))
            
            # 分高低位写入寄存器数据（32位数据拆分为两个16位寄存器）
            # 有功功率：地址0(低16位) + 地址1(高16位)
            active_power_low = active_power_kw & 0xFFFF
            slave_context.setValues(INPUT_REG, REG_ACTIVE_POWER, [active_power_low])
            
            # 需求功率：地址2(低16位) + 地址3(高16位)
            required_power_low = required_power_kw & 0xFFFF
            slave_context.setValues(INPUT_REG, REG_REQUIRED_POWER, [required_power_low])
            
        except KeyError as e:
            raise RuntimeError(f"充电桩设备数据缺失: {e}")
        except ValueError as e:
            raise RuntimeError(f"数据格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"Modbus寄存器更新失败: {e}")
    
    def start_all_modbus_servers(self):
        """启动所有具有IP属性设备的Modbus服务器"""
        self.scan_ip_devices()
        
        for device_info in self.ip_devices:
            self.start_modbus_server(device_info)
    
    def stop_all_modbus_servers(self):
        """停止所有Modbus服务器 - 增强内存清理"""
        try:
            # 逐个停止每个服务器
            for device_key in list(self.modbus_servers.keys()):
                device_type, device_idx = device_key.rsplit('_', 1)
                self.stop_modbus_server(device_type, int(device_idx))
            
            # 防御性清理所有集合（即使单个停止过程中出错，也能确保资源被释放）
            self.modbus_servers.clear()
            self.modbus_contexts.clear()
            self.running_services.clear()
            
            # 清空IP设备列表，避免后续更新尝试
            self.ip_devices.clear()
            
            logger.info("已停止所有Modbus服务器")
            return True
        except Exception as e:
            logger.error(f"停止所有Modbus服务器失败: {e}")
            return False

    def cleanup(self):
        """完整清理Modbus资源"""
        try:
            # 停止所有服务器
            self.stop_all_modbus_servers()
            
            # 清理所有内部引用
            self.modbus_contexts = {}
            self.modbus_servers = {}
            self.running_services = set()
            self.ip_devices = []
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            logger.info("Modbus资源已完全清理")
        except Exception as e:
            logger.error(f"清理Modbus资源时发生错误: {e}")
    
    def update_all_modbus_data(self):
        """更新所有具有IP属性设备的Modbus数据"""
        for device_info in self.ip_devices:
            try:
                device_type = device_info['type']
                device_idx = device_info['index']
                device_key = f"{device_type}_{device_idx}"
                
                # 检查设备服务是否仍在运行
                if device_key not in self.running_services:
                    continue
                    
                # 检查设备上下文是否存在
                if device_key not in self.modbus_contexts:
                    continue
                    
                # 获取正确的slave context
                server_context = self.modbus_contexts[device_key]
                if hasattr(server_context, '__getitem__'):
                    # ModbusServerContext通过[slave_id]访问slave context
                    slave_context = server_context[1]  # 使用slave ID 1
                else:
                    # 如果已经是slave context，直接使用
                    slave_context = server_context
                
                # 从网络模型中获取最新的功率数据
                if device_type == 'meter' and hasattr(self.network_model.net, 'measurement'):
                    if device_idx in self.network_model.net.measurement.index:
                        self.update_meter_context(device_idx, slave_context)
                        
                elif device_type == 'static_generator' and hasattr(self.network_model.net, 'sgen'):
                    if device_idx in self.network_model.net.sgen.index:
                        self.update_sgen_context(device_idx, slave_context)

                elif device_type == 'storage' and hasattr(self.network_model.net, 'storage'):
                    if device_idx in self.network_model.net.storage.index:
                        self.update_storage_context(device_idx, device_info, slave_context)

                elif device_type == 'charger' and hasattr(self.network_model.net, 'load'):  # 充电桩作为负载
                    if device_idx in self.network_model.net.load.index:
                        self.update_charger_context(device_idx, slave_context)
                        
            except Exception as e:
                logger.error(f"更新设备Modbus数据失败 {device_info['name']}: {e}")
    
    
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
        """检查指定设备的服务是否正在运行 - 基于线程实际存活状态"""
        device_key = f"{device_type}_{device_idx}"
        
        # 优先检查线程实际存活状态
        if device_key in self.modbus_servers:
            server_data = self.modbus_servers[device_key]
            if 'thread' in server_data and server_data['thread'].is_alive():
                return True
        
        # 保留原有的检查逻辑作为后备
        return device_key in self.running_services
    
    def get_service_count(self):
        """获取运行服务数量"""
        return len(self.running_services)
    
    def collect_storage_modbus_data(self, device_idx, slave_context):
        """收集单个储能设备的Modbus数据
        
        储能设备保持寄存器功能：
        - 寄存器4：功率设定值 (kW)
        - 寄存器55：开关机控制 (布尔值)
        """
        try:
            device_context = None
            try:
                # 直接通过索引1获取设备上下文
                device_context = slave_context[1]
            except (KeyError, IndexError, TypeError):
                # 如果索引访问失败，保持device_context为None
                pass
            if not device_context:
                return None  # 如果无法获取设备上下文，直接返回None
            # 读取功率设定值（寄存器0）
            try:
                power_setpoint = device_context.getValues(3, 4, 1)[0]
                
                # 先将值转换为int16类型（处理负数）
                if power_setpoint > 32767:  # 检查最高位是否为1（表示负数）
                    power_setpoint = power_setpoint - 65536  # 转换为负数
                
                power_setpoint = power_setpoint / 10.0 / 1000.0  # kW -> MW
            except (IndexError, ValueError, AttributeError):
                power_setpoint = None
                
            # 读取开关机状态（寄存器55）
            try:
                power_on = device_context.getValues(3, 55, 1)[0]
                if power_on == 240:
                    power_on = False
                elif power_on == 243:
                    power_on = True
                else:
                    power_on = None
            except (IndexError, ValueError, AttributeError):
                power_on = None
            # 读取储能并网离网指令 寄存器暂定
            try:
                grid_connected = device_context.getValues(3, 5095, 1)[0]
            except (IndexError, ValueError, AttributeError):
                grid_connected = 0
            
            return {
                'power_on': power_on,
                'power_setpoint': power_setpoint,
                'grid_connected': grid_connected
            }
            
        except Exception as e:
            logger.error(f"收集储能设备 {device_idx} 数据失败: {e}")
            return None
            
    def collect_charger_modbus_data(self, device_idx, slave_context):
        """Collect power limit information from the holding register at address 0 for a single charging pile device"""
        power_limit = None
        
        try:
            # 尝试获取设备上下文的两种方式
            device_context = None
            try:
                # 直接通过索引1获取设备上下文
                device_context = slave_context[1]
            except (KeyError, IndexError, TypeError):
                # 如果索引访问失败，保持device_context为None
                pass
            
            # 如果成功获取设备上下文，则读取功率限制
            if device_context:
                try:
                    result = device_context.getValues(3, 0, 1)
                    if isinstance(result, list) and len(result) > 0:
                        power_limit = result[0] / 1000.0  # Convert kW to MW
                except (TypeError, IndexError):
                    pass
        except Exception:
            pass
        
        return {'power_limit': power_limit}
            
    def collect_sgen_modbus_data(self, device_idx, slave_context):
        """收集单个光伏系统的Modbus数据
        
        光伏系统保持寄存器功能：
        - 寄存器5005：开关机控制 (0=关机, 1=开机)
        - 寄存器5038：有功功率限制 (kW单位)
        - 寄存器5007：有功功率百分比限制 (0-100%)
        """
        try:
            device_context = None
            try:
                # 直接通过索引1获取设备上下文
                device_context = slave_context[1]
            except (KeyError, IndexError, TypeError):
                # 如果索引访问失败，保持device_context为None
                pass
            if not device_context:
                return None  # 如果无法获取设备上下文，直接返回None
            # 读取开关机状态（寄存器5005）
            try:
                power_on = device_context.getValues(3, 5005, 1)[0]
                power_on = bool(power_on)
            except (IndexError, ValueError, AttributeError):
                power_on = True  # 默认启用
                
            # 读取有功功率限制（寄存器5038）
            try:
                power_limit_kw = device_context.getValues(3, 5038, 1)[0]
                # 先将kW转换为MW，再除以10进行额外缩放（根据设备通信协议要求）
                power_limit_mw = power_limit_kw / 1000.0 / 10  # kW -> 缩放后的MW值
            except (IndexError, ValueError, AttributeError):
                power_limit_mw = None
                
            # 读取有功功率百分比限制（寄存器5007）
            try:
                power_percent_limit = device_context.getValues(3, 5007, 1)[0]
                power_percent_limit = min(100, max(0, power_percent_limit))  # 限制在0-100%
            except (IndexError, ValueError, AttributeError):
                power_percent_limit = None
            
            return {
                'power_on': power_on,
                'power_limit_mw': power_limit_mw,
                'power_percent_limit': power_percent_limit
            }
            
        except Exception as e:
            logger.error(f"收集光伏系统 {device_idx} 数据失败: {e}")
            return None
