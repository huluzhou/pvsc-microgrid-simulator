from domain.common.entity import AggregateRoot
from domain.aggregates.topology.value_objects.topology_id import TopologyId
from domain.aggregates.topology.value_objects.topology_status import TopologyStatus, TopologyStatusEnum
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.connection import Connection
from domain.aggregates.topology.events import (
    TopologyCreatedEvent, TopologyUpdatedEvent, DeviceAddedEvent, 
    DeviceRemovedEvent, ConnectionCreatedEvent
)
from domain.aggregates.topology.exceptions import (
    InvalidTopologyException, DeviceNotFoundException, ConnectionException
)
from domain.aggregates.topology.services.topology_connection_rules_service import TopologyConnectionRulesService
from typing import Dict, List, Optional

class MicrogridTopology(AggregateRoot):
    def __init__(self, topology_id: TopologyId, name: str, description: str = ""):
        super().__init__(topology_id)
        self._name = name
        self._description = description
        self._devices: Dict[str, Device] = {}
        self._connections: Dict[str, Connection] = {}
        self._status = TopologyStatus(TopologyStatusEnum.CREATED)
        
        # 发布拓扑创建事件
        self.add_domain_event(TopologyCreatedEvent(
            topology_id=str(topology_id),
            name=name,
            description=description
        ))
    
    @property
    def name(self):
        return self._name
    
    @property
    def description(self):
        return self._description
    
    @property
    def devices(self):
        return list(self._devices.values())
    
    @property
    def connections(self):
        return list(self._connections.values())
    
    @property
    def status(self):
        return self._status
    
    def update_info(self, name: str, description: str):
        self._name = name
        self._description = description
        self.update_timestamp()
        self.add_domain_event(TopologyUpdatedEvent(
            topology_id=str(self.id),
            name=name,
            description=description
        ))
    
    def add_device(self, device: Device):
        device_id_str = str(device.id)
        if device_id_str in self._devices:
            raise InvalidTopologyException(f"Device with id {device_id_str} already exists")
        
        self._devices[device_id_str] = device
        self.update_timestamp()
        self.add_domain_event(DeviceAddedEvent(
            topology_id=str(self.id),
            device_id=device_id_str,
            device_type=str(device.device_type.type)
        ))
    
    def remove_device(self, device_id: str):
        if device_id not in self._devices:
            raise DeviceNotFoundException(f"Device with id {device_id} not found")
        
        # 检查是否有连接使用该设备
        for connection in self._connections.values():
            if connection.source_device_id == device_id or connection.target_device_id == device_id:
                raise ConnectionException(f"Cannot remove device {device_id}, it's used in connections")
        
        del self._devices[device_id]
        self.update_timestamp()
        self.add_domain_event(DeviceRemovedEvent(
            topology_id=str(self.id),
            device_id=device_id
        ))
    
    def get_device(self, device_id: str) -> Device:
        # 检查设备ID是否为字符串，直接比较
        if device_id not in self._devices:
            raise DeviceNotFoundException(f"Device with id {device_id} not found")
        return self._devices[device_id]
    
    def add_connection(self, connection: Connection):
        if connection.id in self._connections:
            raise InvalidTopologyException(f"Connection with id {connection.id} already exists")
        if connection.source_device_id not in self._devices:
            raise DeviceNotFoundException(f"Source device {connection.source_device_id} not found")
        if connection.target_device_id not in self._devices:
            raise DeviceNotFoundException(f"Target device {connection.target_device_id} not found")
        if any(c.source_device_id == connection.source_device_id and c.target_device_id == connection.target_device_id for c in self._connections.values()):
            raise InvalidTopologyException(f"Duplicate connection between {connection.source_device_id} and {connection.target_device_id}")
        src = self._devices[connection.source_device_id]
        tgt = self._devices[connection.target_device_id]
        TopologyConnectionRulesService().enforce_and_apply(self, connection, src, tgt)
        self._connections[connection.id] = connection
        self.update_timestamp()
        self.add_domain_event(ConnectionCreatedEvent(
            topology_id=str(self.id),
            connection_id=str(connection.id),
            source_device_id=connection.source_device_id,
            target_device_id=connection.target_device_id
        ))
    
    def remove_connection(self, connection_id: str):
        if connection_id not in self._connections:
            raise InvalidTopologyException(f"Connection with id {connection_id} not found")
        
        del self._connections[connection_id]
        self.update_timestamp()
    
    def get_connection(self, connection_id: str) -> Connection:
        if connection_id not in self._connections:
            raise InvalidTopologyException(f"Connection with id {connection_id} not found")
        return self._connections[connection_id]
    
    def update_status(self, status: TopologyStatus):
        self._status = status
        self.update_timestamp()
    
