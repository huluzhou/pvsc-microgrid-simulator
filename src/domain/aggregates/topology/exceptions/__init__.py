from domain.common.exceptions.base_exceptions import DomainException

class InvalidTopologyException(DomainException):
    pass

class DeviceNotFoundException(DomainException):
    pass

class ConnectionException(DomainException):
    pass

class TopologyValidationException(DomainException):
    pass
