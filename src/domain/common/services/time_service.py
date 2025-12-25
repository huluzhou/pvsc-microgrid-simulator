from datetime import datetime, timedelta, timezone
from typing import Optional

class TimeService:
    """时间相关服务"""
    
    @staticmethod
    def get_current_datetime(tz: Optional[timezone] = None) -> datetime:
        """获取当前时间"""
        return datetime.now(tz) if tz else datetime.now()
    
    @staticmethod
    def get_current_timestamp(tz: Optional[timezone] = None) -> float:
        """获取当前时间戳（秒）"""
        return TimeService.get_current_datetime(tz).timestamp()
    
    @staticmethod
    def get_current_timestamp_ms(tz: Optional[timezone] = None) -> float:
        """获取当前时间戳（毫秒）"""
        return TimeService.get_current_timestamp(tz) * 1000
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间"""
        return dt.strftime(format_str)
    
    @staticmethod
    def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """解析时间字符串"""
        return datetime.strptime(date_str, format_str)
    
    @staticmethod
    def add_duration(dt: datetime, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> datetime:
        """添加时间间隔"""
        return dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    
    @staticmethod
    def subtract_duration(dt: datetime, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> datetime:
        """减去时间间隔"""
        return dt - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    
    @staticmethod
    def get_duration_between(start: datetime, end: datetime) -> timedelta:
        """获取两个时间之间的间隔"""
        return end - start
    
    @staticmethod
    def is_datetime_in_past(dt: datetime, tz: Optional[timezone] = None) -> bool:
        """检查时间是否在过去"""
        return dt < TimeService.get_current_datetime(tz)
    
    @staticmethod
    def is_datetime_in_future(dt: datetime, tz: Optional[timezone] = None) -> bool:
        """检查时间是否在未来"""
        return dt > TimeService.get_current_datetime(tz)
    
    @staticmethod
    def truncate_datetime(dt: datetime, unit: str = "second") -> datetime:
        """截断时间到指定单位"""
        if unit == "year":
            return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif unit == "month":
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif unit == "day":
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif unit == "hour":
            return dt.replace(minute=0, second=0, microsecond=0)
        elif unit == "minute":
            return dt.replace(second=0, microsecond=0)
        elif unit == "second":
            return dt.replace(microsecond=0)
        elif unit == "millisecond":
            return dt.replace(microsecond=dt.microsecond // 1000 * 1000)
        else:
            raise ValueError(f"Invalid truncation unit: {unit}")
