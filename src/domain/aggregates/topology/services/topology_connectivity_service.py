from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.connection import Connection
from typing import Dict, Set, List

class TopologyConnectivityService:
    def __init__(self):
        pass
    
    def check_connectivity(self, topology: MicrogridTopology) -> Dict[str, any]:
        # 构建邻接表
        adjacency_list = self._build_adjacency_list(topology)
        
        # 检查连通性
        connected_components = self._find_connected_components(adjacency_list)
        
        # 检查是否有孤立设备
        isolated_devices = self._find_isolated_devices(topology, adjacency_list)
        
        return {
            "connected_components": connected_components,
            "number_of_components": len(connected_components),
            "isolated_devices": isolated_devices,
            "is_fully_connected": len(connected_components) == 1 and len(isolated_devices) == 0,
            "total_devices": len(topology.devices)
        }
    
    def _build_adjacency_list(self, topology: MicrogridTopology) -> Dict[str, List[str]]:
        adjacency_list = {device.id: [] for device in topology.devices}
        
        for connection in topology.connections:
            if connection.is_active:
                # 添加双向连接
                adjacency_list[connection.source_device_id].append(connection.target_device_id)
                adjacency_list[connection.target_device_id].append(connection.source_device_id)
        
        return adjacency_list
    
    def _find_connected_components(self, adjacency_list: Dict[str, List[str]]) -> List[Set[str]]:
        visited = set()
        components = []
        
        for device_id in adjacency_list:
            if device_id not in visited:
                component = self._dfs(device_id, adjacency_list, visited)
                components.append(component)
        
        return components
    
    def _dfs(self, start: str, adjacency_list: Dict[str, List[str]], visited: Set[str]) -> Set[str]:
        stack = [start]
        component = set()
        
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                component.add(current)
                stack.extend([neighbor for neighbor in adjacency_list[current] if neighbor not in visited])
        
        return component
    
    def _find_isolated_devices(self, topology: MicrogridTopology, adjacency_list: Dict[str, List[str]]) -> List[str]:
        isolated = []
        for device in topology.devices:
            if not adjacency_list[device.id]:
                isolated.append(device.id)
        return isolated
    
    def find_shortest_path(self, topology: MicrogridTopology, start_device_id: str, end_device_id: str) -> List[str]:
        # 使用BFS查找最短路径
        adjacency_list = self._build_adjacency_list(topology)
        
        if start_device_id not in adjacency_list or end_device_id not in adjacency_list:
            return []
        
        visited = {start_device_id: None}
        queue = [start_device_id]
        
        while queue:
            current = queue.pop(0)
            if current == end_device_id:
                break
            
            for neighbor in adjacency_list[current]:
                if neighbor not in visited:
                    visited[neighbor] = current
                    queue.append(neighbor)
        
        # 重建路径
        path = []
        current = end_device_id
        while current:
            path.append(current)
            current = visited.get(current)
        
        return path[::-1]
