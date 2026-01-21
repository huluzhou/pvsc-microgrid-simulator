"""
AI 内核抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class AIKernel(ABC):
    """AI 内核抽象接口"""
    
    @abstractmethod
    def predict(self, device_ids: List[str], prediction_horizon: int, prediction_type: str) -> Dict[str, Any]:
        """数据预测"""
        pass
    
    @abstractmethod
    def optimize(self, objective: str, constraints: List[str], time_horizon: int) -> Dict[str, Any]:
        """运行优化"""
        pass
    
    @abstractmethod
    def get_recommendations(self, device_ids: List[str]) -> List[str]:
        """获取优化建议"""
        pass
    
    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        pass
