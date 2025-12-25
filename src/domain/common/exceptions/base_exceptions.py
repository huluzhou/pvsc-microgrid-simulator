class DomainException(Exception):
    """所有领域异常的基类"""
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.code = code
        self.message = message

class BusinessRuleViolationException(DomainException):
    """业务规则违反异常"""
    def __init__(self, message: str, rule: str = None, code: str = "BUSINESS_RULE_VIOLATION"):
        super().__init__(message, code)
        self.rule = rule

class EntityNotFoundException(DomainException):
    """实体未找到异常"""
    def __init__(self, entity_type: str, entity_id: str = None, code: str = "ENTITY_NOT_FOUND"):
        message = f"{entity_type} not found"
        if entity_id:
            message = f"{entity_type} with id {entity_id} not found"
        super().__init__(message, code)
        self.entity_type = entity_type
        self.entity_id = entity_id

class ValidationException(DomainException):
    """验证异常"""
    def __init__(self, message: str, field: str = None, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code)
        self.field = field

class InvariantViolationException(DomainException):
    """不变量违反异常"""
    def __init__(self, message: str, invariant: str = None, code: str = "INVARIANT_VIOLATION"):
        super().__init__(message, code)
        self.invariant = invariant

class CommunicationException(DomainException):
    """通信异常基类"""
    def __init__(self, message: str, source: str = None, destination: str = None, code: str = "COMMUNICATION_ERROR"):
        super().__init__(message, code)
        self.source = source
        self.destination = destination

class CalculationException(DomainException):
    """计算异常基类"""
    def __init__(self, message: str, calculation_type: str = None, code: str = "CALCULATION_ERROR"):
        super().__init__(message, code)
        self.calculation_type = calculation_type
