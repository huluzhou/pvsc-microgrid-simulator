from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar('T')

class Specification(ABC, Generic[T]):
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        pass
    
    def __and__(self, other):
        return AndSpecification(self, other)
    
    def __or__(self, other):
        return OrSpecification(self, other)
    
    def __invert__(self):
        return NotSpecification(self)

class AndSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]):
        self._left = left
        self._right = right
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(candidate)

class OrSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]):
        self._left = left
        self._right = right
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(candidate)

class NotSpecification(Specification[T]):
    def __init__(self, specification: Specification[T]):
        self._specification = specification
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._specification.is_satisfied_by(candidate)
