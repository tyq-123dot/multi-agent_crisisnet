import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from loguru import logger
from crisisnet_common.enhanced_models import MemoryEntry, KeyEvent


class RingBufferMemory:
    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self.buffer: deque = deque(maxlen=max_entries)
    
    def add(
        self,
        tick: int,
        observation: Dict,
        action: Dict,
        result: Dict
    ):
        entry = MemoryEntry(
            tick=tick,
            observation=observation,
            action=action,
            result=result
        )
        self.buffer.append(entry)
        logger.debug(f"Added memory entry at tick {tick}")
    
    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        return list(self.buffer)[-n:]
    
    def get_by_tick_range(self, start_tick: int, end_tick: int) -> List[MemoryEntry]:
        return [e for e in self.buffer if start_tick <= e.tick <= end_tick]
    
    def clear(self):
        self.buffer.clear()
        logger.info("Ring buffer memory cleared")
    
    def build_context_string(self, n: int = 5) -> str:
        entries = self.get_recent(n)
        if not entries:
            return "No recent history."
        
        context_parts = ["Recent History:"]
        for i, entry in enumerate(reversed(entries), 1):
            part = f"\n{i}. Tick {entry.tick}:"
            part += f"\n   Observation: {entry.observation}"
            part += f"\n   Action: {entry.action}"
            part += f"\n   Result: {entry.result}"
            context_parts.append(part)
        
        return "".join(context_parts)


class LongTermMemory:
    def __init__(self, decay_hours: float = 24.0):
        self.decay_hours = decay_hours
        self.events: Dict[str, KeyEvent] = {}
        self.location_index: Dict[str, List[str]] = {}
        self.type_index: Dict[str, List[str]] = {}
    
    def add_event(
        self,
        event_type: str,
        location: str,
        details: Dict,
        importance: float = 1.0
    ) -> str:
        event_id = str(uuid.uuid4())
        event = KeyEvent(
            event_id=event_id,
            event_type=event_type,
            location=location,
            details=details,
            importance=importance
        )
        
        self.events[event_id] = event
        
        if location not in self.location_index:
            self.location_index[location] = []
        self.location_index[location].append(event_id)
        
        if event_type not in self.type_index:
            self.type_index[event_type] = []
        self.type_index[event_type].append(event_id)
        
        logger.debug(f"Added long-term event: {event_type} at {location}")
        return event_id
    
    def get_events_by_location(self, location: str, include_archived: bool = False) -> List[KeyEvent]:
        event_ids = self.location_index.get(location, [])
        events = [self.events[eid] for eid in event_ids if eid in self.events]
        if not include_archived:
            events = [e for e in events if not e.archived]
        return self._apply_decay(events)
    
    def get_events_by_type(self, event_type: str, include_archived: bool = False) -> List[KeyEvent]:
        event_ids = self.type_index.get(event_type, [])
        events = [self.events[eid] for eid in event_ids if eid in self.events]
        if not include_archived:
            events = [e for e in events if not e.archived]
        return self._apply_decay(events)
    
    def _apply_decay(self, events: List[KeyEvent]) -> List[KeyEvent]:
        now = datetime.utcnow()
        decay_cutoff = now - timedelta(hours=self.decay_hours)
        
        return [
            e for e in events
            if e.timestamp > decay_cutoff
        ]
    
    def archive_event(self, event_id: str):
        if event_id in self.events:
            self.events[event_id].archived = True
            logger.debug(f"Archived event {event_id}")
    
    def get_relevant_context(
        self,
        location: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        max_events: int = 10
    ) -> str:
        events: List[KeyEvent] = []
        
        if location:
            events.extend(self.get_events_by_location(location))
        if event_types:
            for et in event_types:
                events.extend(self.get_events_by_type(et))
        
        events = list({e.event_id: e for e in events}.values())
        events.sort(key=lambda e: (e.importance, e.timestamp), reverse=True)
        events = events[:max_events]
        
        if not events:
            return "No relevant long-term history."
        
        context_parts = ["Relevant Past Events:"]
        for i, event in enumerate(events, 1):
            part = f"\n{i}. {event.event_type} at {event.location} ({event.timestamp.strftime('%H:%M')}):"
            part += f"\n   Details: {event.details}"
            part += f"\n   Importance: {event.importance}"
            context_parts.append(part)
        
        return "".join(context_parts)
    
    def clear(self):
        self.events.clear()
        self.location_index.clear()
        self.type_index.clear()
        logger.info("Long-term memory cleared")
