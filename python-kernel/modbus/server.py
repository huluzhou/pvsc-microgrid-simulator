"""
Modbus TCP 服务器
使用 pymodbus 实现
"""

from typing import Dict, Any, Optional
import asyncio
from pymodbus.server.async_io import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.device import ModbusDeviceIdentification
from .handler import ModbusHandler


class ModbusServer:
    """Modbus TCP 服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 502):
        self.host = host
        self.port = port
        self.server_task: Optional[asyncio.Task] = None
        self.handler = ModbusHandler()
        self.device_registers: Dict[str, Dict[int, int]] = {}  # device_id -> {address: value}
    
    def set_device_register(self, device_id: str, address: int, value: int):
        """设置设备寄存器值"""
        if device_id not in self.device_registers:
            self.device_registers[device_id] = {}
        self.device_registers[device_id][address] = value
    
    def get_device_register(self, device_id: str, address: int) -> int:
        """获取设备寄存器值"""
        return self.device_registers.get(device_id, {}).get(address, 0)
    
    async def start(self):
        """启动 Modbus 服务器"""
        if self.server_task is not None:
            return  # 已经启动
        
        # 创建数据存储
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*100),  # 离散输入
            co=ModbusSequentialDataBlock(0, [0]*100),  # 线圈
            hr=ModbusSequentialDataBlock(0, [0]*100),  # 保持寄存器
            ir=ModbusSequentialDataBlock(0, [0]*100),  # 输入寄存器
        )
        
        context = ModbusServerContext(slaves={1: store}, single=True)
        
        # 设备标识
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'PVSC Microgrid Simulator'
        identity.ProductCode = 'MG-SIM'
        identity.VendorUrl = 'https://github.com/pvsc/microgrid-simulator'
        identity.ProductName = 'Microgrid Simulator'
        identity.ModelName = 'Simulator'
        identity.MajorMinorRevision = '1.0.0'
        
        # 启动服务器
        self.server_task = asyncio.create_task(
            StartTcpServer(
                context=context,
                identity=identity,
                address=(self.host, self.port)
            )
        )
    
    async def stop(self):
        """停止 Modbus 服务器"""
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            self.server_task = None
