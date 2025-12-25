from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from domain.aggregates.topology.value_objects.topology_status import TopologyStatusEnum
from domain.aggregates.topology.value_objects.device_type import DeviceTypeEnum
from domain.aggregates.topology.value_objects.connection_type import ConnectionTypeEnum


@dataclass
class PositionDTO:
    """位置数据传输对象"""
    x: float
    y: float
    z: Optional[float] = None


@dataclass
class LocationDTO:
    """地理位置数据传输对象"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None


@dataclass
class DevicePropertiesDTO:
    """设备属性数据传输对象"""
    capacity: Optional[float] = None
    voltage_level: Optional[float] = None
    current_rating: Optional[float] = None
    power_factor: Optional[float] = None
    efficiency: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class DeviceDTO:
    """设备数据传输对象"""
    id: str
    device_type: DeviceTypeEnum
    name: str
    position: PositionDTO
    created_at: datetime
    updated_at: datetime
    location: Optional[LocationDTO] = None
    properties: Optional[DevicePropertiesDTO] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ConnectionDTO:
    """连接数据传输对象"""
    id: str
    source_device_id: str
    target_device_id: str
    connection_type: ConnectionTypeEnum
    created_at: datetime
    updated_at: datetime
    properties: Optional[Dict[str, Any]] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TopologyDTO:
    """拓扑数据传输对象"""
    id: str
    name: str
    status: TopologyStatusEnum
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    devices: List[DeviceDTO] = field(default_factory=list)
    connections: List[ConnectionDTO] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TopologyListDTO:
    """拓扑列表数据传输对象"""
    items: List[TopologyDTO]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


@dataclass
class CreateTopologyRequestDTO:
    """创建拓扑请求数据传输对象"""
    name: str
    description: Optional[str] = None
    status: Optional[TopologyStatusEnum] = TopologyStatusEnum.CREATED
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CreateTopologyResponseDTO:
    """创建拓扑响应数据传输对象"""
    topology_id: str
    name: str
    status: TopologyStatusEnum
    message: str


@dataclass
class AddDeviceRequestDTO:
    """添加设备请求数据传输对象"""
    device_type: DeviceTypeEnum
    name: str
    position: PositionDTO
    location: Optional[LocationDTO] = None
    properties: Optional[DevicePropertiesDTO] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AddDeviceResponseDTO:
    """添加设备响应数据传输对象"""
    device_id: str
    name: str
    device_type: DeviceTypeEnum
    message: str
    
    @staticmethod
    def from_domain(device, name: str, message: str) -> "AddDeviceResponseDTO":
        """从领域实体创建DTO
        
        Args:
            device: Device领域实体
            name: 设备名称
            message: 响应消息
            
        Returns:
            AddDeviceResponseDTO实例
        """
        return AddDeviceResponseDTO(
            device_id=str(device.id),
            name=name,
            device_type=device.device_type.type,
            message=message
        )


@dataclass
class CreateConnectionRequestDTO:
    """创建连接请求数据传输对象"""
    source_device_id: str
    target_device_id: str
    connection_type: ConnectionTypeEnum
    properties: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CreateConnectionResponseDTO:
    """创建连接响应数据传输对象"""
    connection_id: str
    source_device_id: str
    target_device_id: str
    message: str


@dataclass
class ValidateTopologyResponseDTO:
    """验证拓扑响应数据传输对象"""
    topology_id: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class OptimizeTopologyResponseDTO:
    """优化拓扑响应数据传输对象"""
    topology_id: str
    optimization_result: Dict[str, Any]
    message: str
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TopologyStatisticsDTO:
    """拓扑统计数据传输对象"""
    topology_id: str
    total_devices: int
    total_connections: int
    device_type_distribution: Dict[DeviceTypeEnum, int]
    status: TopologyStatusEnum
    last_updated: datetime
