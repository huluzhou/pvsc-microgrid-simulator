from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.value_objects.device_type import DeviceType, DeviceTypeEnum
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.position import Position
from typing import Optional

class Switch(Device):
    def __init__(self, switch_id, properties: DeviceProperties, 
                 location: Optional[Location] = None, position: Optional[Position] = None):
        super().__init__(switch_id, DeviceType(DeviceTypeEnum.SWITCH), properties, location, position)
        self._is_closed = properties.get_property("is_closed", False)
    
    @property
    def is_closed(self):
        return self._is_closed
    
    def close(self):
        self._is_closed = True
        new_properties = DeviceProperties({**self.properties.properties, "is_closed": True})
        self.update_properties(new_properties)
    
    def open(self):
        self._is_closed = False
        new_properties = DeviceProperties({**self.properties.properties, "is_closed": False})
        self.update_properties(new_properties)
