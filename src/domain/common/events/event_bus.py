from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Type
from .domain_event import DomainEvent

class EventHandler(ABC):
    """事件处理器接口"""
    
    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """处理领域事件"""
        pass

class EventBus(ABC):
    """事件总线接口"""
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """订阅事件类型"""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """取消订阅事件类型"""
        pass
    
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """发布领域事件"""
        pass

class InMemoryEventBus(EventBus):
    """内存事件总线实现"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
    
    def publish(self, event: DomainEvent) -> None:
        event_type = event.event_type()
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                handler.handle(event)
