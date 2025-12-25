from typing import Dict, Optional
from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.ports.topology_repository_port import TopologyRepositoryPort


class InMemoryTopologyRepository(TopologyRepositoryPort):
    """内存拓扑存储库实现
    
    使用内存字典存储拓扑实体，用于开发和测试
    """
    
    def __init__(self):
        self._topologies: Dict[str, MicrogridTopology] = {}
    
    def save(self, topology: MicrogridTopology) -> MicrogridTopology:
        """保存拓扑实体"""
        topology_id_str = str(topology.id)
        self._topologies[topology_id_str] = topology
        return topology
    
    def get(self, topology_id: str) -> Optional[MicrogridTopology]:
        """根据ID获取拓扑实体"""
        return self._topologies.get(topology_id)
    
    def update(self, topology: MicrogridTopology) -> MicrogridTopology:
        """更新拓扑实体"""
        return self.save(topology)  # 内存存储中，保存和更新是相同操作
    
    def delete(self, topology_id: str) -> bool:
        """删除拓扑实体"""
        if topology_id in self._topologies:
            del self._topologies[topology_id]
            return True
        return False
