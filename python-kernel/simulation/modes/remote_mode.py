"""
远程模式（Modbus TCP）
"""

from typing import Dict, Any
import time


class RemoteMode:
    """远程模式处理器（通过 Modbus TCP 接收外部控制）"""
    
    def __init__(self):
        self.device_data: Dict[str, Dict[str, Any]] = {}
    
    def update_device_data(self, device_id: str, data: Dict[str, Any]):
        """更新设备数据（从 Modbus 接收）"""
        self.device_data[device_id] = {
            **data,
            "timestamp": time.time(),
        }
    
    def get_data(self, device_id: str) -> Dict[str, Any]:
        """获取设备数据"""
        return self.device_data.get(device_id, {
            "voltage": 0.0,
            "current": 0.0,
            "power": 0.0,
            "timestamp": time.time(),
        })
