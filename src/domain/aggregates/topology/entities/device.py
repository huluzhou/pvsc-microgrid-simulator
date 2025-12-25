from domain.common.entity import Entity
from domain.aggregates.topology.value_objects.device_type import DeviceType
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.position import Position
from domain.aggregates.topology.value_objects.device_id import DeviceId
from typing import Optional

class Device(Entity):
    def __init__(self, device_id, device_type: DeviceType, properties: DeviceProperties, 
                 location: Optional[Location] = None, position: Optional[Position] = None):
        super().__init__(device_id)
        self._device_type = device_type
        self._properties = properties
        self._location = location
        self._position = position
        self._is_active = True
    
    @property
    def device_type(self):
        return self._device_type
    
    @property
    def properties(self):
        return self._properties
    
    @property
    def location(self):
        return self._location
    
    @property
    def position(self):
        return self._position
    
    @property
    def is_active(self):
        return self._is_active
    
    def activate(self):
        self._is_active = True
        self.update_timestamp()
    
    def deactivate(self):
        self._is_active = False
        self.update_timestamp()
    
    def update_properties(self, new_properties: DeviceProperties):
        self._properties = new_properties
        self.update_timestamp()
    
    def update_location(self, new_location: Location):
        self._location = new_location
        self.update_timestamp()
    
    def update_position(self, new_position: Position):
        self._position = new_position
        self.update_timestamp()
