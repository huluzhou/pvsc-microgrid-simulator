"""
计算内核抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union


class PowerCalculationKernel(ABC):
    """功率计算内核抽象接口"""
    
    @abstractmethod
    def calculate_power_flow(self, topology_data_or_net: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """
        执行潮流计算
        
        Args:
            topology_data_or_net: 必须是已转换的网络对象（由适配器层转换）
                                 不接受原始拓扑数据字典，请使用对应的适配器进行转换
        
        Returns:
            计算结果字典，包含converged、errors、devices等字段
        
        注意：
            - 新代码必须使用适配器层（TopologyAdapter）进行数据转换
            - 适配器层提供统一的错误处理和验证功能
            - 避免在计算内核中重复实现转换逻辑
        """
        pass
    
    @abstractmethod
    def convert_topology(self, topology: Dict[str, Any]) -> Any:
        """
        将系统拓扑转换为内核格式
        
        ⚠️ 已弃用：此方法不应再使用，请使用适配器层（TopologyAdapter）进行转换。
        
        原因：
        - 避免重复的转换逻辑，统一使用适配器层
        - 适配器层提供更好的错误处理和验证功能
        - 确保代码维护的一致性
        
        此方法保留在接口中仅用于向后兼容，实现应抛出NotImplementedError。
        """
        pass
    
    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        pass
