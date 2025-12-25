from enum import Enum
from domain.common.value_objects.base_value_object import ValueObject

class DeviceTypeEnum(Enum):
    GENERATOR = "GENERATOR"
    LOAD = "LOAD"
    STORAGE = "STORAGE"
    LINE = "LINE"
    TRANSFORMER = "TRANSFORMER"
    SWITCH = "SWITCH"
    NODE = "NODE"
    BUS = "BUS"
    STATIC_GENERATOR = "STATIC_GENERATOR"
    CHARGER = "CHARGER"
    METER = "METER"
    EXTERNAL_GRID = "EXTERNAL_GRID"

class DeviceType(ValueObject):
    def __init__(self, type_value: DeviceTypeEnum):
        self._type = type_value
    
    @property
    def type(self):
        return self._type
    
    def _get_eq_values(self):
        return [self._type]
