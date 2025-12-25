from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.connection import Connection
from typing import Dict, List, Any

class TopologyOptimizationService:
    def __init__(self):
        pass
    
    def optimize(self, topology: MicrogridTopology) -> Dict[str, Any]:
        # 这里实现拓扑优化逻辑
        # 目前提供基础的优化建议
        optimization_results = {
            "suggestions": [],
            "optimization_score": 0.0,
            "before_optimization": {
                "total_devices": len(topology.devices),
                "total_connections": len(topology.connections)
            },
            "after_optimization": {
                "total_devices": len(topology.devices),
                "total_connections": len(topology.connections)
            }
        }
        
        # 检查是否有冗余连接
        redundant_connections = self._find_redundant_connections(topology)
        if redundant_connections:
            optimization_results["suggestions"].extend([
                f"Remove redundant connection {conn.id}" for conn in redundant_connections
            ])
        
        # 检查是否有孤立设备
        from domain.aggregates.topology.services.topology_connectivity_service import TopologyConnectivityService
        connectivity_service = TopologyConnectivityService()
        connectivity_result = connectivity_service.check_connectivity(topology)
        
        if connectivity_result["isolated_devices"]:
            optimization_results["suggestions"].extend([
                f"Connect isolated device {device_id} to the main network" 
                for device_id in connectivity_result["isolated_devices"]
            ])
        
        # 计算优化分数
        optimization_results["optimization_score"] = self._calculate_optimization_score(
            topology, len(redundant_connections), len(connectivity_result["isolated_devices"])
        )
        
        return optimization_results
    
    def _find_redundant_connections(self, topology: MicrogridTopology) -> List[Connection]:
        # 简单的冗余连接检测：如果两个设备之间有多个连接，则认为是冗余
        device_pairs = {}
        redundant_connections = []
        
        for connection in topology.connections:
            # 创建一个有序的设备对，确保 (a,b) 和 (b,a) 被视为同一对
            pair = tuple(sorted([connection.source_device_id, connection.target_device_id]))
            
            if pair in device_pairs:
                # 已经存在连接，当前连接是冗余的
                redundant_connections.append(connection)
            else:
                device_pairs[pair] = connection
        
        return redundant_connections
    
    def _calculate_optimization_score(self, topology: MicrogridTopology, 
                                      num_redundant: int, num_isolated: int) -> float:
        # 计算优化分数，范围0-100
        base_score = 100.0
        
        # 减去冗余连接的扣分
        if topology.connections:
            redundant_penalty = (num_redundant / len(topology.connections)) * 30
        else:
            redundant_penalty = 0
        
        # 减去孤立设备的扣分
        if topology.devices:
            isolated_penalty = (num_isolated / len(topology.devices)) * 50
        else:
            isolated_penalty = 0
        
        # 计算最终分数
        final_score = base_score - redundant_penalty - isolated_penalty
        return max(0.0, min(100.0, final_score))
