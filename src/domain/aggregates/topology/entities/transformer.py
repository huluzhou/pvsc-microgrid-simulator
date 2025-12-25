from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.value_objects.device_type import DeviceType, DeviceTypeEnum
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.position import Position
from typing import Optional

class Transformer(Device):
    def __init__(self, transformer_id, properties: DeviceProperties, 
                 location: Optional[Location] = None, position: Optional[Position] = None):
        super().__init__(transformer_id, DeviceType(DeviceTypeEnum.TRANSFORMER), properties, location, position)
        self._primary_voltage = properties.get_property("primary_voltage", 0.0)
        self._secondary_voltage = properties.get_property("secondary_voltage", 0.0)
        self._power_rating = properties.get_property("power_rating", 0.0)
    
    @property
    def primary_voltage(self):
        return self._primary_voltage
    
    @property
    def secondary_voltage(self):
        return self._secondary_voltage
    
    @property
    def power_rating(self):
        return self._power_rating
    
    def update_voltage_rating(self, primary_voltage: float, secondary_voltage: float):
        self._primary_voltage = primary_voltage
        self._secondary_voltage = secondary_voltage
        new_properties = DeviceProperties({
            **self.properties.properties,
            "primary_voltage": primary_voltage,
            "secondary_voltage": secondary_voltage
        })
        self.update_properties(new_properties)
    
    def update_power_rating(self, power_rating: float):
        self._power_rating = power_rating
        new_properties = DeviceProperties({**self.properties.properties, "power_rating": power_rating})
        self.update_properties(new_properties)
