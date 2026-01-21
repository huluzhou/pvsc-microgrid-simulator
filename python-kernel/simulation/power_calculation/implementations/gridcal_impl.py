"""
GridCal 计算内核实现（可选）
"""

from typing import Dict, Any, List
from ..interface import PowerCalculationKernel


class GridCalKernel(PowerCalculationKernel):
    """GridCal 计算内核实现"""
    
    def calculate_power_flow(self, topology_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行潮流计算"""
        # 将在后续阶段实现
        return {"status": "not_implemented"}
    
    def convert_topology(self, topology: Dict[str, Any]) -> Dict[str, Any]:
        """将系统拓扑转换为 GridCal 格式"""
        # 将在后续阶段实现
        return {}
    
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        return ["ac_power_flow", "large_scale"]
