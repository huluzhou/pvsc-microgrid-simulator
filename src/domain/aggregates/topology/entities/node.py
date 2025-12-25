from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.value_objects.device_type import DeviceType, DeviceTypeEnum
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.position import Position
from typing import Optional

class Node(Device):
    def __init__(self, node_id, properties: DeviceProperties, 
                 location: Optional[Location] = None, position: Optional[Position] = None):
        super().__init__(node_id, DeviceType(DeviceTypeEnum.NODE), properties, location, position)
        self._voltage_level = properties.get_property("voltage_level", 0.0)
    
    @property
    def voltage_level(self):
        return self._voltage_level
    
    def update_voltage_level(self, voltage_level: float):
        self._voltage_level = voltage_level
        new_properties = DeviceProperties({**self.properties.properties, "voltage_level": voltage_level})
        self.update_properties(new_properties)
