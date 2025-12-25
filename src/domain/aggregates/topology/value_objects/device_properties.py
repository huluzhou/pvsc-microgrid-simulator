from typing import Dict, Any
from domain.common.value_objects.base_value_object import ValueObject

class DeviceProperties(ValueObject):
    def __init__(self, properties: Dict[str, Any]):
        self._properties = properties.copy()
    
    @property
    def properties(self):
        return self._properties.copy()
    
    def get_property(self, key: str, default: Any = None) -> Any:
        return self._properties.get(key, default)
    
    def _get_eq_values(self):
        return [tuple(sorted(self._properties.items()))]
