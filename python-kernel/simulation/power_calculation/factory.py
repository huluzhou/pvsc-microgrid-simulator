"""
计算内核工厂
支持同时创建计算内核和对应的适配器
"""

from typing import Optional, Tuple
from .interface import PowerCalculationKernel
from ..adapters.topology_adapter import TopologyAdapter


class PowerKernelFactory:
    """功率计算内核工厂"""
    
    @staticmethod
    def create(kernel_type: str) -> Optional[PowerCalculationKernel]:
        """创建功率计算内核实例"""
        if kernel_type == "pandapower":
            try:
                from .implementations.pandapower_impl import PandapowerKernel
                return PandapowerKernel()
            except ImportError:
                return None
        elif kernel_type == "pypsa":
            try:
                from .implementations.pypsa_impl import PyPSAKernel
                return PyPSAKernel()
            except ImportError:
                return None
        elif kernel_type == "gridcal":
            try:
                from .implementations.gridcal_impl import GridCalKernel
                return GridCalKernel()
            except ImportError:
                return None
        else:
            return None
    
    @staticmethod
    def create_with_adapter(kernel_type: str) -> Optional[Tuple[PowerCalculationKernel, TopologyAdapter]]:
        """
        创建计算内核和对应的适配器
        
        Returns:
            (计算内核, 适配器) 元组，如果创建失败返回None
        """
        if kernel_type == "pandapower":
            try:
                from .implementations.pandapower_impl import PandapowerKernel
                from ..adapters.pandapower_adapter import PandapowerTopologyAdapter
                return PandapowerKernel(), PandapowerTopologyAdapter()
            except ImportError:
                return None
        elif kernel_type == "pypsa":
            try:
                from .implementations.pypsa_impl import PyPSAKernel
                # PyPSA适配器尚未实现
                return PyPSAKernel(), None
            except ImportError:
                return None
        elif kernel_type == "gridcal":
            try:
                from .implementations.gridcal_impl import GridCalKernel
                # GridCal适配器尚未实现
                return GridCalKernel(), None
            except ImportError:
                return None
        else:
            return None
