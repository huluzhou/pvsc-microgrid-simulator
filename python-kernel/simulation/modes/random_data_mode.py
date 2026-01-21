"""
随机数据模式
"""

from typing import Dict, Any
import random
import math
import time


class RandomDataMode:
    """随机数据模式处理器"""
    
    def __init__(self):
        self.base_time = time.time()
    
    def get_data(self, device_id: str) -> Dict[str, Any]:
        """生成随机设备数据"""
        t = time.time() - self.base_time
        
        # 生成正弦波数据
        voltage = 220 + 10 * math.sin(2 * math.pi * t / 10)
        current = 10 + 5 * math.sin(2 * math.pi * t / 8)
        power = voltage * current
        
        return {
            "voltage": round(voltage, 2),
            "current": round(current, 2),
            "power": round(power, 2),
            "timestamp": time.time(),
        }
