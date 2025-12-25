from typing import List, TypeVar, Generic
from domain.common.specifications.base_specification import Specification

T = TypeVar('T')

class SpecificationEvaluator(Generic[T]):
    """规格评估器"""
    
    @staticmethod
    def evaluate(candidate: T, specification: Specification[T]) -> bool:
        """评估单个规格"""
        return specification.is_satisfied_by(candidate)
    
    @staticmethod
    def evaluate_all(candidate: T, specifications: List[Specification[T]]) -> bool:
        """评估所有规格，全部满足才返回True"""
        return all(spec.is_satisfied_by(candidate) for spec in specifications)
    
    @staticmethod
    def evaluate_single_spec(candidate: T, specification: Specification[T]) -> bool:
        """评估单个规格"""
        return specification.is_satisfied_by(candidate)
    
    @staticmethod
    def evaluate_any(candidate: T, specifications: List[Specification[T]]) -> bool:
        """评估所有规格，只要有一个满足就返回True"""
        return any(spec.is_satisfied_by(candidate) for spec in specifications)
    
    @staticmethod
    def filter(candidates: List[T], specification: Specification[T]) -> List[T]:
        """根据规格过滤候选对象列表"""
        return [candidate for candidate in candidates if specification.is_satisfied_by(candidate)]
    
    @staticmethod
    def count_satisfied(candidates: List[T], specification: Specification[T]) -> int:
        """统计满足规格的候选对象数量"""
        return sum(1 for candidate in candidates if specification.is_satisfied_by(candidate))
