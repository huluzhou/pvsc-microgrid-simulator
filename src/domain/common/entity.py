from abc import ABC
from typing import Optional
from datetime import datetime

class Entity(ABC):
    def __init__(self, entity_id):
        self._id = entity_id
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
    
    @property
    def id(self):
        return self._id
    
    @property
    def created_at(self):
        return self._created_at
    
    @property
    def updated_at(self):
        return self._updated_at
    
    def update_timestamp(self):
        self._updated_at = datetime.now()
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self._id == other.id
    
    def __hash__(self):
        return hash(self._id)

class AggregateRoot(Entity):
    def __init__(self, aggregate_id):
        super().__init__(aggregate_id)
        self._domain_events = []
    
    def add_domain_event(self, event):
        self._domain_events.append(event)
    
    def clear_domain_events(self):
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
