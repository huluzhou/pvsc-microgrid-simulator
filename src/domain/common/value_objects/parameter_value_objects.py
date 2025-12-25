from typing import Optional
from .base_value_object import ValueObject

class ParameterValue(ValueObject):
    """带单位和验证规则的参数值"""
    def __init__(self, value: float, unit: str, min_value: Optional[float] = None, max_value: Optional[float] = None):
        if not isinstance(value, (int, float)):
            raise ValueError("Parameter value must be a number")
        if not unit or not isinstance(unit, str):
            raise ValueError("Unit must be a non-empty string")
        
        if min_value is not None and value < min_value:
            raise ValueError(f"Value {value} is less than minimum allowed {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"Value {value} is greater than maximum allowed {max_value}")
        
        self._value = float(value)
        self._unit = unit
        self._min_value = min_value
        self._max_value = max_value
    
    @property
    def value(self) -> float:
        return self._value
    
    @property
    def unit(self) -> str:
        return self._unit
    
    @property
    def min_value(self) -> Optional[float]:
        return self._min_value
    
    @property
    def max_value(self) -> Optional[float]:
        return self._max_value
    
    def _get_eq_values(self):
        return [self._value, self._unit, self._min_value, self._max_value]
    
    def __str__(self) -> str:
        return f"{self._value} {self._unit}"

class UnitOfMeasure(ValueObject):
    """度量单位"""
    def __init__(self, symbol: str, name: str):
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")
        
        self._symbol = symbol
        self._name = name
    
    @property
    def symbol(self) -> str:
        return self._symbol
    
    @property
    def name(self) -> str:
        return self._name
    
    def _get_eq_values(self):
        return [self._symbol, self._name]
    
    def __str__(self) -> str:
        return self._symbol
