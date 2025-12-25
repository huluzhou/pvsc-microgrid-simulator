from abc import ABC, abstractmethod
from typing import Optional
from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.value_objects.topology_id import TopologyId


class TopologyRepositoryPort(ABC):
    """拓扑存储库端口
    
    定义了拓扑实体的持久化操作接口，是应用层与基础设施层之间的边界
    """
    
    @abstractmethod
    def save(self, topology: MicrogridTopology) -> MicrogridTopology:
        """保存拓扑实体
        
        Args:
            topology: 拓扑实体
            
        Returns:
            保存后的拓扑实体
        """
        pass
    
    @abstractmethod
    def get(self, topology_id: str) -> Optional[MicrogridTopology]:
        """根据ID获取拓扑实体
        
        Args:
            topology_id: 拓扑ID字符串
            
        Returns:
            拓扑实体，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def update(self, topology: MicrogridTopology) -> MicrogridTopology:
        """更新拓扑实体
        
        Args:
            topology: 拓扑实体
            
        Returns:
            更新后的拓扑实体
        """
        pass
    
    @abstractmethod
    def delete(self, topology_id: str) -> bool:
        """删除拓扑实体
        
        Args:
            topology_id: 拓扑ID字符串
            
        Returns:
            删除成功返回True，否则返回False
        """
        pass
