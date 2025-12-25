from typing import Optional
from .base_value_object import ValueObject

class EntityId(ValueObject):
    """通用实体标识符"""
    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("EntityId must be a non-empty string")
        self._value = value
    
    @property
    def value(self) -> str:
        return self._value
    
    def _get_eq_values(self):
        return [self._value]
    
    def __str__(self) -> str:
        return self._value

class AggregateId(EntityId):
    """聚合根标识符"""
    pass
