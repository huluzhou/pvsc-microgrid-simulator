"""
计算内核工厂
"""

from typing import Optional
from .interface import PowerCalculationKernel


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
