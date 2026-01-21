"""
手动模式
"""

from typing import Dict, Any, Optional
import time


class ManualMode:
    """手动模式处理器"""
    
    def __init__(self):
        self.device_settings: Dict[str, Dict[str, Any]] = {}
    
    def set_device_setting(self, device_id: str, setting: Dict[str, Any]):
        """设置设备参数"""
        if device_id not in self.device_settings:
            self.device_settings[device_id] = {}
        self.device_settings[device_id].update(setting)
    
    def get_data(self, device_id: str) -> Dict[str, Any]:
        """获取设备数据（基于手动设置）"""
        settings = self.device_settings.get(device_id, {})
        
        return {
            "voltage": settings.get("voltage", 220.0),
            "current": settings.get("current", 0.0),
            "power": settings.get("power", 0.0),
            "timestamp": time.time(),
        }
