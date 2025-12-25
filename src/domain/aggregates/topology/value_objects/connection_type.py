from enum import Enum
from domain.common.value_objects.base_value_object import ValueObject

class ConnectionTypeEnum(Enum):
    SERIES = "SERIES"
    PARALLEL = "PARALLEL"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    UNIDIRECTIONAL = "UNIDIRECTIONAL"

class ConnectionType(ValueObject):
    def __init__(self, type_value: ConnectionTypeEnum):
        self._type = type_value
    
    @property
    def type(self):
        return self._type
    
    def _get_eq_values(self):
        return [self._type]
