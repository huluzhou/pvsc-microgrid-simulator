from typing import Any, Dict, List, Callable
from domain.common.exceptions.base_exceptions import ValidationException

class ValidationService:
    """通用验证服务"""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
        """验证必填字段"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationException(f"Missing required fields: {', '.join(missing_fields)}")
    
    @staticmethod
    def validate_field_type(data: Dict[str, Any], field: str, expected_type: type) -> None:
        """验证字段类型"""
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                raise ValidationException(f"Field {field} must be of type {expected_type.__name__}")
    
    @staticmethod
    def validate_field_range(data: Dict[str, Any], field: str, min_value: float = None, max_value: float = None) -> None:
        """验证数值字段范围"""
        if field in data and data[field] is not None:
            value = data[field]
            if not isinstance(value, (int, float)):
                raise ValidationException(f"Field {field} must be a number")
            
            if min_value is not None and value < min_value:
                raise ValidationException(f"Field {field} must be >= {min_value}")
            if max_value is not None and value > max_value:
                raise ValidationException(f"Field {field} must be <= {max_value}")
    
    @staticmethod
    def validate_field_length(data: Dict[str, Any], field: str, min_length: int = None, max_length: int = None) -> None:
        """验证字符串字段长度"""
        if field in data and data[field] is not None:
            value = data[field]
            if not isinstance(value, str):
                raise ValidationException(f"Field {field} must be a string")
            
            length = len(value)
            if min_length is not None and length < min_length:
                raise ValidationException(f"Field {field} must be at least {min_length} characters long")
            if max_length is not None and length > max_length:
                raise ValidationException(f"Field {field} must be at most {max_length} characters long")
    
    @staticmethod
    def validate_with_custom_rule(data: Dict[str, Any], field: str, rule: Callable[[Any], bool], error_message: str) -> None:
        """使用自定义规则验证字段"""
        if field in data and data[field] is not None:
            if not rule(data[field]):
                raise ValidationException(error_message, field=field)
