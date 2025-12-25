from typing import Dict, List, Callable
from domain.common.events.event_bus import EventBus, EventHandler
from domain.common.events.domain_event import DomainEvent
from infrastructure.third_party.events.signals import event_bus as _signals_bus


class BlinkerEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        def _wrapper(sender=None, **kwargs):
            evt = kwargs.get("domain_event")
            if isinstance(evt, DomainEvent):
                handler.handle(evt)

        _signals_bus.subscribe(event_type, _wrapper)
        self._handlers.setdefault(event_type, []).append(_wrapper)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        wrappers = self._handlers.get(event_type, [])
        for w in list(wrappers):
            _signals_bus.unsubscribe(event_type, w)
            wrappers.remove(w)
        if not wrappers and event_type in self._handlers:
            del self._handlers[event_type]

    def publish(self, event: DomainEvent) -> None:
        _signals_bus.publish(event.event_type(), event_data={"source": event.source}, domain_event=event)
