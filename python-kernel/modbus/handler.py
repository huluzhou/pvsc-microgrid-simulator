"""
Modbus 请求处理器
"""

from typing import Dict, Any


class ModbusHandler:
    """Modbus 请求处理器"""
    
    def handle_read_holding_registers(self, address: int, count: int) -> list:
        """处理读取保持寄存器请求"""
        # 将在后续阶段实现
        return [0] * count
    
    def handle_write_holding_registers(self, address: int, values: list):
        """处理写入保持寄存器请求"""
        # 将在后续阶段实现
        pass
