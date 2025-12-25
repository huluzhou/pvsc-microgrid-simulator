from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ports.outbound.device.device_control_port import DeviceControlPort


class ProtocolAdapterInterface(ABC):
    """通信协议适配器基础接口"""
    
    @abstractmethod
    def connect(self, config: dict):
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def send_data(self, data: dict, destination: str = None):
        """发送数据"""
        pass
    
    @abstractmethod
    def receive_data(self, timeout: int = None) -> dict:
        """接收数据"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass
    
    @abstractmethod
    def register_data_handler(self, handler):
        """注册数据处理器"""
        pass


class ModbusAdapter(ProtocolAdapterInterface):
    """Modbus协议适配器实现"""
    
    def __init__(self, device_control_port: DeviceControlPort):
        """初始化Modbus适配器
        
        Args:
            device_control_port: 设备控制端口，用于与领域层交互
        """
        self.device_control_port = device_control_port
        self._connected = False
        self._handlers = []
    
    def connect(self, config: dict):
        """建立Modbus连接
        
        Args:
            config: 连接配置，包含host、port等信息
        """
        # 实际实现中，这里会使用modbus_tk或pymodbus库建立连接
        self._connected = True
    
    def disconnect(self):
        """断开Modbus连接"""
        self._connected = False
    
    def send_data(self, data: dict, destination: str = None):
        """发送Modbus数据
        
        Args:
            data: 要发送的数据
            destination: 目标设备地址（可选）
        """
        # 实际实现中，这里会将数据转换为Modbus协议格式并发送
        pass
    
    def receive_data(self, timeout: int = None) -> dict:
        """接收Modbus数据
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            接收到的数据
        """
        # 实际实现中，这里会接收Modbus数据并转换为字典格式
        return {}
    
    def is_connected(self) -> bool:
        """检查Modbus连接状态
        
        Returns:
            连接状态（True/False）
        """
        return self._connected
    
    def register_data_handler(self, handler):
        """注册数据处理器
        
        Args:
            handler: 数据处理器函数
        """
        self._handlers.append(handler)
    
    def read_coils(self, address: int, count: int):
        """读取线圈状态
        
        Args:
            address: 起始地址
            count: 数量
        
        Returns:
            线圈状态列表
        """
        return self.device_control_port.read_device_state("MODBUS", {
            "function": "READ_COILS", 
            "address": address, 
            "count": count
        })
    
    def write_coil(self, address: int, value: bool):
        """写入线圈状态
        
        Args:
            address: 地址
            value: 值
        
        Returns:
            操作结果
        """
        return self.device_control_port.write_device_state("MODBUS", {
            "function": "WRITE_COIL", 
            "address": address, 
            "value": value
        })
    
    def read_registers(self, address: int, count: int):
        """读取保持寄存器
        
        Args:
            address: 起始地址
            count: 数量
        
        Returns:
            寄存器值列表
        """
        return self.device_control_port.read_device_state("MODBUS", {
            "function": "READ_REGISTERS", 
            "address": address, 
            "count": count
        })
    
    def write_register(self, address: int, value: int):
        """写入保持寄存器
        
        Args:
            address: 地址
            value: 值
        
        Returns:
            操作结果
        """
        return self.device_control_port.write_device_state("MODBUS", {
            "function": "WRITE_REGISTER", 
            "address": address, 
            "value": value
        })
