"""拓扑用例端口定义

这些端口定义了应用层与适配器层之间的接口。
用例实现这些端口，适配器调用这些端口。

注意：这些端口位于应用层，因为它们依赖于应用层的Commands和DTOs。
领域层只保留仓储端口（Repository Ports）。
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from application.commands.topology.topology_commands import (
    CreateTopologyCommand,
    AddDeviceCommand,
    UpdateDeviceCommand,
    RemoveDeviceCommand,
    CreateConnectionCommand,
    UpdateConnectionCommand,
    RemoveConnectionCommand,
    UpdateTopologyStatusCommand,
    ValidateTopologyCommand,
    OptimizeTopologyCommand
)
from application.dtos.topology.topology_dtos import (
    TopologyDTO,
    DeviceDTO,
    ConnectionDTO,
    CreateTopologyResponseDTO,
    AddDeviceResponseDTO,
    CreateConnectionResponseDTO,
    ValidateTopologyResponseDTO,
    OptimizeTopologyResponseDTO
)


class TopologyCreationPort(ABC):
    """拓扑创建端口"""
    
    @abstractmethod
    def create_topology(self, command: CreateTopologyCommand) -> CreateTopologyResponseDTO:
        """创建拓扑
        
        Args:
            command: 创建拓扑命令
            
        Returns:
            创建拓扑响应DTO
        """
        pass


class TopologyDeviceManagementPort(ABC):
    """拓扑设备管理端口"""
    
    @abstractmethod
    def add_device(self, command: AddDeviceCommand) -> AddDeviceResponseDTO:
        """添加设备
        
        Args:
            command: 添加设备命令
            
        Returns:
            添加设备响应DTO
        """
        pass
    
    @abstractmethod
    def update_device(self, command: UpdateDeviceCommand) -> Dict[str, Any]:
        """更新设备
        
        Args:
            command: 更新设备命令
            
        Returns:
            更新设备响应
        """
        pass
    
    @abstractmethod
    def remove_device(self, command: RemoveDeviceCommand) -> Dict[str, Any]:
        """移除设备
        
        Args:
            command: 移除设备命令
            
        Returns:
            移除设备响应
        """
        pass
    
    @abstractmethod
    def update_topology_status(self, command: UpdateTopologyStatusCommand) -> TopologyDTO:
        """更新拓扑状态
        
        Args:
            command: 更新拓扑状态命令
            
        Returns:
            更新后的拓扑DTO
        """
        pass


class TopologyConnectionManagementPort(ABC):
    """拓扑连接管理端口"""
    
    @abstractmethod
    def create_connection(self, command: CreateConnectionCommand) -> CreateConnectionResponseDTO:
        """创建连接
        
        Args:
            command: 创建连接命令
            
        Returns:
            创建连接响应DTO
        """
        pass
    
    @abstractmethod
    def update_connection(self, command: UpdateConnectionCommand) -> Dict[str, Any]:
        """更新连接
        
        Args:
            command: 更新连接命令
            
        Returns:
            更新连接响应
        """
        pass
    
    @abstractmethod
    def remove_connection(self, command: RemoveConnectionCommand) -> Dict[str, Any]:
        """移除连接
        
        Args:
            command: 移除连接命令
            
        Returns:
            移除连接响应
        """
        pass


class TopologyValidationPort(ABC):
    """拓扑验证端口"""
    
    @abstractmethod
    def validate_topology(self, command: ValidateTopologyCommand) -> ValidateTopologyResponseDTO:
        """验证拓扑
        
        Args:
            command: 验证拓扑命令
            
        Returns:
            验证拓扑响应DTO
        """
        pass


class TopologyOptimizationPort(ABC):
    """拓扑优化端口"""
    
    @abstractmethod
    def optimize_topology(self, command: OptimizeTopologyCommand) -> OptimizeTopologyResponseDTO:
        """优化拓扑
        
        Args:
            command: 优化拓扑命令
            
        Returns:
            优化拓扑响应DTO
        """
        pass


class TopologyQueryPort(ABC):
    """拓扑查询端口"""
    
    @abstractmethod
    def get_topology(self, topology_id: str) -> Optional[TopologyDTO]:
        """根据ID获取拓扑
        
        Args:
            topology_id: 拓扑ID
            
        Returns:
            拓扑DTO，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def list_topologies(self, filters: Optional[Dict[str, Any]] = None) -> List[TopologyDTO]:
        """获取拓扑列表
        
        Args:
            filters: 过滤条件（可选）
            
        Returns:
            拓扑DTO列表
        """
        pass
    
    @abstractmethod
    def get_topology_devices(self, topology_id: str) -> List[DeviceDTO]:
        """获取拓扑设备列表
        
        Args:
            topology_id: 拓扑ID
            
        Returns:
            设备DTO列表
        """
        pass
    
    @abstractmethod
    def get_topology_connections(self, topology_id: str) -> List[ConnectionDTO]:
        """获取拓扑连接列表
        
        Args:
            topology_id: 拓扑ID
            
        Returns:
            连接DTO列表
        """
        pass

