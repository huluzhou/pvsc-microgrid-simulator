from datetime import datetime, timedelta
from typing import Optional
from .base_value_object import ValueObject

class TimeRange(ValueObject):
    """时间范围"""
    def __init__(self, start_time: datetime, end_time: datetime):
        if not isinstance(start_time, datetime):
            raise ValueError("Start time must be a datetime object")
        if not isinstance(end_time, datetime):
            raise ValueError("End time must be a datetime object")
        if end_time < start_time:
            raise ValueError("End time must be after start time")
        
        self._start_time = start_time
        self._end_time = end_time
    
    @property
    def start_time(self) -> datetime:
        return self._start_time
    
    @property
    def end_time(self) -> datetime:
        return self._end_time
    
    @property
    def duration(self) -> timedelta:
        return self._end_time - self._start_time
    
    def contains(self, time: datetime) -> bool:
        """检查时间是否在范围内"""
        return self._start_time <= time <= self._end_time
    
    def overlaps_with(self, other: 'TimeRange') -> bool:
        """检查是否与另一个时间范围重叠"""
        return not (self._end_time < other._start_time or self._start_time > other._end_time)
    
    def _get_eq_values(self):
        return [self._start_time, self._end_time]
    
    def __str__(self) -> str:
        return f"{self._start_time} to {self._end_time}"

class Timestamp(ValueObject):
    """带精度的时间戳"""
    def __init__(self, value: datetime, precision: str = "second"):
        if not isinstance(value, datetime):
            raise ValueError("Timestamp must be a datetime object")
        
        valid_precisions = ["millisecond", "second", "minute", "hour"]
        if precision not in valid_precisions:
            raise ValueError(f"Invalid precision. Must be one of: {', '.join(valid_precisions)}")
        
        # 根据精度截断时间
        if precision == "millisecond":
            self._value = value
        elif precision == "second":
            self._value = value.replace(microsecond=0)
        elif precision == "minute":
            self._value = value.replace(second=0, microsecond=0)
        elif precision == "hour":
            self._value = value.replace(minute=0, second=0, microsecond=0)
        
        self._precision = precision
    
    @property
    def value(self) -> datetime:
        return self._value
    
    @property
    def precision(self) -> str:
        return self._precision
    
    def _get_eq_values(self):
        return [self._value, self._precision]
    
    def __str__(self) -> str:
        return str(self._value)
