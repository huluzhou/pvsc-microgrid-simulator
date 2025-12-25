from domain.common.specifications.base_specification import Specification
from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.connection import Connection
from typing import Any

class ValidTopologySpecification(Specification):
    def is_satisfied_by(self, topology: MicrogridTopology) -> bool:
        # 检查拓扑是否有效：至少有一个设备，所有连接都指向存在的设备
        if not topology.devices:
            return False
        
        for connection in topology.connections:
            source_exists = any(device.id == connection.source_device_id for device in topology.devices)
            target_exists = any(device.id == connection.target_device_id for device in topology.devices)
            if not source_exists or not target_exists:
                return False
        
        return True

class DeviceExistsSpecification(Specification):
    def __init__(self, device_id: str):
        self._device_id = device_id
    
    def is_satisfied_by(self, topology: MicrogridTopology) -> bool:
        return any(device.id == self._device_id for device in topology.devices)

class ConnectionValidSpecification(Specification):
    def is_satisfied_by(self, connection: Connection) -> bool:
        # 检查连接是否有效：源设备和目标设备不同
        return connection.source_device_id != connection.target_device_id

class CompleteTopologySpecification(Specification):
    def is_satisfied_by(self, topology: MicrogridTopology) -> bool:
        # 检查拓扑是否完整：至少有一个设备和一个连接
        if not topology.devices or not topology.connections:
            return False
        
        # 检查所有设备是否都有连接
        connected_devices = set()
        for connection in topology.connections:
            connected_devices.add(connection.source_device_id)
            connected_devices.add(connection.target_device_id)
        
        return len(connected_devices) == len(topology.devices)
