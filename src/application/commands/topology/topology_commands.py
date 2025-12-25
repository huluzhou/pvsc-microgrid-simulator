from dataclasses import dataclass, field
from typing import Optional, List, Dict
from domain.aggregates.topology.value_objects.topology_id import TopologyId
from domain.aggregates.topology.value_objects.topology_status import TopologyStatusEnum
from domain.aggregates.topology.value_objects.device_type import DeviceTypeEnum
from domain.aggregates.topology.value_objects.connection_type import ConnectionTypeEnum
from domain.aggregates.topology.value_objects.position import Position
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties


@dataclass(frozen=True)
class CreateTopologyCommand:
    """创建拓扑命令"""
    name: str
    description: Optional[str] = None
    status: TopologyStatusEnum = TopologyStatusEnum.CREATED
    metadata: Optional[Dict[str, any]] = field(default_factory=dict)
    topology_id: Optional[TopologyId] = None


@dataclass(frozen=True)
class AddDeviceCommand:
    """添加设备命令"""
    topology_id: TopologyId
    device_type: DeviceTypeEnum
    name: str
    position: Position
    location: Optional[Location] = None
    properties: Optional[DeviceProperties] = None
    metadata: Optional[Dict[str, any]] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateDeviceCommand:
    """更新设备命令"""
    topology_id: TopologyId
    device_id: str
    name: Optional[str] = None
    position: Optional[Position] = None
    location: Optional[Location] = None
    properties: Optional[DeviceProperties] = None
    metadata: Optional[Dict[str, any]] = None


@dataclass(frozen=True)
class RemoveDeviceCommand:
    """移除设备命令"""
    topology_id: TopologyId
    device_id: str


@dataclass(frozen=True)
class CreateConnectionCommand:
    """创建连接命令"""
    topology_id: TopologyId
    source_device_id: str
    target_device_id: str
    connection_type: ConnectionTypeEnum
    properties: Optional[Dict[str, any]] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateConnectionCommand:
    """更新连接命令"""
    topology_id: TopologyId
    connection_id: str
    properties: Dict[str, any]


@dataclass(frozen=True)
class RemoveConnectionCommand:
    """移除连接命令"""
    topology_id: TopologyId
    connection_id: str


@dataclass(frozen=True)
class UpdateTopologyStatusCommand:
    """更新拓扑状态命令"""
    topology_id: TopologyId
    status: TopologyStatusEnum


@dataclass(frozen=True)
class ValidateTopologyCommand:
    """验证拓扑命令"""
    topology_id: TopologyId
    validation_rules: Optional[List[str]] = None


@dataclass(frozen=True)
class OptimizeTopologyCommand:
    """优化拓扑命令"""
    topology_id: TopologyId
    optimization_goals: Optional[List[str]] = None
    constraints: Optional[Dict[str, any]] = field(default_factory=dict)


@dataclass(frozen=True)
class NewTopologyCommand:
    name: str
    description: Optional[str] = None


@dataclass(frozen=True)
class OpenTopologyCommand:
    file_path: str


@dataclass(frozen=True)
class SaveTopologyCommand:
    topology_id: TopologyId
    file_path: str


@dataclass(frozen=True)
class ImportTopologyCommand:
    file_path: str


@dataclass(frozen=True)
class ExportTopologyCommand:
    topology_id: TopologyId
    file_path: str


@dataclass(frozen=True)
class UndoCommand:
    topology_id: Optional[TopologyId] = None


@dataclass(frozen=True)
class RedoCommand:
    topology_id: Optional[TopologyId] = None
