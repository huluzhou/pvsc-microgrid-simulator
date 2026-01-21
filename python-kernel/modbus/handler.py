"""
Modbus 请求处理器
"""

from typing import Dict, Any, List, Optional


class ModbusHandler:
    """Modbus 请求处理器"""
    
    def __init__(self):
        self.registers: Dict[int, int] = {}  # address -> value
        self.device_mapping: Dict[str, Dict[int, int]] = {}  # device_id -> {address: value}
    
    def map_device_registers(self, device_id: str, base_address: int, registers: Dict[str, int]):
        """
        映射设备数据到寄存器
        
        Args:
            device_id: 设备ID
            base_address: 基础地址
            registers: 寄存器映射 {"voltage": 0, "current": 1, "power": 2}
        """
        if device_id not in self.device_mapping:
            self.device_mapping[device_id] = {}
        
        for key, offset in registers.items():
            address = base_address + offset
            self.device_mapping[device_id][key] = address
    
    def handle_read_holding_registers(self, address: int, count: int) -> List[int]:
        """处理读取保持寄存器请求"""
        result = []
        for i in range(count):
            addr = address + i
            value = self.registers.get(addr, 0)
            result.append(value)
        return result
    
    def handle_write_holding_registers(self, address: int, values: List[int]):
        """处理写入保持寄存器请求"""
        for i, value in enumerate(values):
            self.registers[address + i] = value
    
    def update_device_data(self, device_id: str, data: Dict[str, float]):
        """更新设备数据到寄存器"""
        if device_id not in self.device_mapping:
            return
        
        mapping = self.device_mapping[device_id]
        for key, address in mapping.items():
            if key in data:
                # 将浮点数转换为整数（乘以1000以保留3位小数）
                value = int(data[key] * 1000)
                self.registers[address] = value
    
    def get_device_data(self, device_id: str) -> Dict[str, float]:
        """从寄存器获取设备数据"""
        if device_id not in self.device_mapping:
            return {}
        
        result = {}
        mapping = self.device_mapping[device_id]
        for key, address in mapping.items():
            value = self.registers.get(address, 0)
            # 将整数转换回浮点数
            result[key] = value / 1000.0
        
        return result
