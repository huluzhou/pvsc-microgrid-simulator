from domain.common.entity import Entity
from domain.aggregates.topology.value_objects.connection_type import ConnectionType
from typing import Optional

class Connection(Entity):
    def __init__(self, connection_id, source_device_id, target_device_id, connection_type: ConnectionType, 
                 properties: Optional[dict] = None):
        super().__init__(connection_id)
        self._source_device_id = source_device_id
        self._target_device_id = target_device_id
        self._connection_type = connection_type
        self._properties = properties or {}
        self._is_active = True
    
    @property
    def source_device_id(self):
        return self._source_device_id
    
    @property
    def target_device_id(self):
        return self._target_device_id
    
    @property
    def connection_type(self):
        return self._connection_type
    
    @property
    def properties(self):
        return self._properties.copy()
    
    @property
    def is_active(self):
        return self._is_active
    
    def activate(self):
        self._is_active = True
        self.update_timestamp()
    
    def deactivate(self):
        self._is_active = False
        self.update_timestamp()
    
    def update_properties(self, new_properties: dict):
        self._properties = new_properties.copy()
        self.update_timestamp()
