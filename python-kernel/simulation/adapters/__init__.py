"""
拓扑数据适配器模块
提供拓扑数据到不同计算内核的转换接口
"""

from .topology_adapter import TopologyAdapter, AdapterResult
from .pandapower_adapter import PandapowerTopologyAdapter

__all__ = [
    'TopologyAdapter',
    'AdapterResult',
    'PandapowerTopologyAdapter',
]
