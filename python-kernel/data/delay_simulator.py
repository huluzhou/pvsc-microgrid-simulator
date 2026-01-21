"""
延迟模拟
"""

import time
import random
from typing import Dict, Any


class DelaySimulator:
    """延迟模拟器"""
    
    def simulate_device_response_delay(self, device_capacity: float) -> float:
        """模拟设备响应延迟"""
        # 基础延迟 + 容量系数 × 设备容量
        base_delay = 0.1  # 100ms
        capacity_coefficient = 0.01  # 每 kWh 增加 10ms
        delay = base_delay + capacity_coefficient * device_capacity
        
        # 添加随机抖动
        jitter = random.uniform(-0.05, 0.05)
        return max(0.05, delay + jitter)
    
    def simulate_communication_delay(self, is_local: bool = True) -> float:
        """模拟通信延迟"""
        if is_local:
            return random.uniform(0.01, 0.05)  # 10-50ms
        else:
            return random.uniform(0.05, 0.2)  # 50-200ms
