from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

class DomainEvent(ABC):
    def __init__(self, source: str, aggregate_id: Optional[str] = None):
        self._event_id = str(uuid.uuid4())
        self._timestamp = datetime.now()
        self._source = source
        self._aggregate_id = aggregate_id
        self._metadata: Dict[str, Any] = {}
    
    @property
    def event_id(self) -> str:
        return self._event_id
    
    @property
    def timestamp(self) -> datetime:
        return self._timestamp
    
    @property
    def source(self) -> str:
        return self._source
    
    @property
    def aggregate_id(self) -> Optional[str]:
        return self._aggregate_id
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata.copy()
    
    def add_metadata(self, key: str, value: Any):
        self._metadata[key] = value
    
    @abstractmethod
    def event_type(self) -> str:
        pass
