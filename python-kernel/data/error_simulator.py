"""
误差模拟
"""

import random
from typing import Dict, Any


class ErrorSimulator:
    """误差模拟器"""
    
    def apply_meter_error(self, value: float, error_range: float = 0.02) -> float:
        """应用电表测量误差"""
        # 误差范围: ±0.5% ~ ±2%（可配置）
        error = random.uniform(-error_range, error_range)
        return value * (1 + error)
    
    def apply_device_error(self, value: float, device_type: str) -> float:
        """应用设备测量误差"""
        # 误差范围: ±1% ~ ±5%（根据设备类型）
        error_ranges = {
            "pv": 0.02,      # ±2%
            "storage": 0.03, # ±3%
            "load": 0.01,    # ±1%
            "charger": 0.05, # ±5%
        }
        error_range = error_ranges.get(device_type, 0.02)
        error = random.uniform(-error_range, error_range)
        return value * (1 + error)
