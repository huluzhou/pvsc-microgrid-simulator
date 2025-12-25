from abc import ABC
from typing import Any, List

class ValueObject(ABC):
    def __eq__(self, other):
        if not isinstance(other, ValueObject):
            return False
        return self._get_eq_values() == other._get_eq_values()
    
    def __hash__(self):
        return hash(tuple(self._get_eq_values()))
    
    def _get_eq_values(self) -> List[Any]:
        raise NotImplementedError("子类必须实现_get_eq_values方法")
