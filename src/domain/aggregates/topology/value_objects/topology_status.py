from enum import Enum
from domain.common.value_objects.base_value_object import ValueObject

class TopologyStatusEnum(Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    INVALID = "INVALID"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"

class TopologyStatus(ValueObject):
    def __init__(self, status_value: TopologyStatusEnum):
        self._status = status_value
    
    @property
    def status(self):
        return self._status
    
    def _get_eq_values(self):
        return [self._status]
