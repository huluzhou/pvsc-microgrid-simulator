from typing import Dict, Any
from domain.common.value_objects.base_value_object import ValueObject

class Location(ValueObject):
    def __init__(self, latitude: float, longitude: float, altitude: float = 0.0):
        self._latitude = latitude
        self._longitude = longitude
        self._altitude = altitude
    
    @property
    def latitude(self):
        return self._latitude
    
    @property
    def longitude(self):
        return self._longitude
    
    @property
    def altitude(self):
        return self._altitude
    
    def _get_eq_values(self):
        return [self._latitude, self._longitude, self._altitude]
