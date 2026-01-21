"""
仿真引擎核心
"""

from typing import Dict, Any, List
from .modes.random_data_mode import RandomDataMode
from .modes.manual_mode import ManualMode
from .modes.remote_mode import RemoteMode
from .modes.historical_data_mode import HistoricalDataMode


class SimulationEngine:
    """仿真引擎"""
    
    def __init__(self):
        self.modes = {
            "random_data": RandomDataMode(),
            "manual": ManualMode(),
            "remote": RemoteMode(),
            "historical_data": HistoricalDataMode(),
        }
        self.device_modes: Dict[str, str] = {}  # device_id -> mode
        self.is_running = False
    
    def set_device_mode(self, device_id: str, mode: str):
        """设置设备工作模式"""
        if mode not in self.modes:
            raise ValueError(f"Unknown mode: {mode}")
        self.device_modes[device_id] = mode
    
    def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """获取设备数据"""
        mode = self.device_modes.get(device_id, "random_data")
        mode_handler = self.modes[mode]
        return mode_handler.get_data(device_id)
    
    def start(self):
        """启动仿真"""
        self.is_running = True
    
    def stop(self):
        """停止仿真"""
        self.is_running = False
