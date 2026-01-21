"""
AI 内核抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AIKernel(ABC):
    """AI 内核抽象接口"""
    
    @abstractmethod
    def predict(self, data: Dict[str, Any], model_type: str) -> Dict[str, Any]:
        """数据预测"""
        pass
    
    @abstractmethod
    def optimize(self, problem: Dict[str, Any], method: str) -> Dict[str, Any]:
        """运行优化"""
        pass
    
    @abstractmethod
    def train_model(self, training_data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """训练模型"""
        pass
