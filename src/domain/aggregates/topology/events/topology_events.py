from domain.common.events.domain_event import DomainEvent
from datetime import datetime

class TopologyCreatedEvent(DomainEvent):
    def __init__(self, topology_id: str, name: str, description: str):
        super().__init__(source="MicrogridTopology", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.name = name
        self.description = description
    
    def event_type(self) -> str:
        return "TopologyCreated"

class TopologyUpdatedEvent(DomainEvent):
    def __init__(self, topology_id: str, name: str, description: str):
        super().__init__(source="MicrogridTopology", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.name = name
        self.description = description
    
    def event_type(self) -> str:
        return "TopologyUpdated"

class DeviceAddedEvent(DomainEvent):
    def __init__(self, topology_id: str, device_id: str, device_type: str):
        super().__init__(source="MicrogridTopology", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.device_id = device_id
        self.device_type = device_type
    
    def event_type(self) -> str:
        return "DeviceAdded"

class DeviceRemovedEvent(DomainEvent):
    def __init__(self, topology_id: str, device_id: str):
        super().__init__(source="MicrogridTopology", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.device_id = device_id
    
    def event_type(self) -> str:
        return "DeviceRemoved"

class ConnectionCreatedEvent(DomainEvent):
    def __init__(self, topology_id: str, connection_id: str, source_device_id: str, target_device_id: str):
        super().__init__(source="MicrogridTopology", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.connection_id = connection_id
        self.source_device_id = source_device_id
        self.target_device_id = target_device_id
    
    def event_type(self) -> str:
        return "ConnectionCreated"

class TopologyValidatedEvent(DomainEvent):
    def __init__(self, topology_id: str, is_valid: bool, validation_results: dict):
        super().__init__(source="TopologyValidationService", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.is_valid = is_valid
        self.validation_results = validation_results
    
    def event_type(self) -> str:
        return "TopologyValidated"

class TopologyValidationFailedEvent(DomainEvent):
    def __init__(self, topology_id: str, errors: list):
        super().__init__(source="TopologyValidationService", aggregate_id=topology_id)
        self.topology_id = topology_id
        self.errors = errors
    
    def event_type(self) -> str:
        return "TopologyValidationFailed"
