"""
AI 内核工厂
"""

from typing import Optional
from .interface import AIKernel


class AIKernelFactory:
    """AI 内核工厂"""
    
    @staticmethod
    def create(kernel_type: str) -> Optional[AIKernel]:
        """创建 AI 内核实例"""
        if kernel_type == "pytorch":
            try:
                from .implementations.pytorch_impl import PyTorchKernel
                return PyTorchKernel()
            except ImportError:
                return None
        elif kernel_type == "tensorflow":
            try:
                from .implementations.tensorflow_impl import TensorFlowKernel
                return TensorFlowKernel()
            except ImportError:
                return None
        elif kernel_type == "gym":
            try:
                from .implementations.gym_impl import GymKernel
                return GymKernel()
            except ImportError:
                return None
        else:
            return None
