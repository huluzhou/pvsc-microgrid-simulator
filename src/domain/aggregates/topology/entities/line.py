from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.value_objects.device_type import DeviceType, DeviceTypeEnum
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.position import Position
from typing import Optional

class Line(Device):
    def __init__(self, line_id, properties: DeviceProperties, 
                 location: Optional[Location] = None, position: Optional[Position] = None):
        super().__init__(line_id, DeviceType(DeviceTypeEnum.LINE), properties, location, position)
        self._resistance = properties.get_property("resistance", 0.0)
        self._reactance = properties.get_property("reactance", 0.0)
        self._capacitance = properties.get_property("capacitance", 0.0)
    
    @property
    def resistance(self):
        return self._resistance
    
    @property
    def reactance(self):
        return self._reactance
    
    @property
    def capacitance(self):
        return self._capacitance
    
    def update_impedance(self, resistance: float, reactance: float, capacitance: float):
        self._resistance = resistance
        self._reactance = reactance
        self._capacitance = capacitance
        new_properties = DeviceProperties({
            **self.properties.properties,
            "resistance": resistance,
            "reactance": reactance,
            "capacitance": capacitance
        })
        self.update_properties(new_properties)
