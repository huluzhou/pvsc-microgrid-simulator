"""
计算内核抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class PowerCalculationKernel(ABC):
    """功率计算内核抽象接口"""
    
    @abstractmethod
    def calculate_power_flow(self, topology_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行潮流计算"""
        pass
    
    @abstractmethod
    def convert_topology(self, topology: Dict[str, Any]) -> Dict[str, Any]:
        """将系统拓扑转换为内核格式"""
        pass
    
    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        pass
