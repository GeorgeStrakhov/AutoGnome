"""Memory system for AutoGnomes"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from collections import deque

@dataclass
class MemoryEvent:
    """A single memory event"""
    timestamp: datetime
    event_type: str
    details: str

class ShortTermMemory:
    """Short term memory system that tracks recent events"""
    def __init__(self, capacity: int = 60):  # Default to remembering last 60 events
        self.events: deque[MemoryEvent] = deque(maxlen=capacity)
        self.last_state: Optional[str] = None
        self.last_transition_time: Optional[datetime] = None
        self._last_record_time: Optional[datetime] = None
    
    def record_state(self, state: str, details: str = "") -> Optional[MemoryEvent]:
        """Record a state and return a transition event if state changed"""
        now = datetime.now()
        
        # Only record state changes at most once per second
        if self._last_record_time and (now - self._last_record_time).total_seconds() < 1.0:
            return None
            
        self._last_record_time = now
        
        # If this is a new state, record the transition
        if self.last_state is not None and state != self.last_state:
            event = MemoryEvent(
                timestamp=now,
                event_type="transition",
                details=f"Changed from {self.last_state} to {state}. {details}"
            )
            self.events.append(event)
            self.last_state = state
            self.last_transition_time = now
            return event
        
        # If this is the first state, just record it
        if self.last_state is None:
            self.last_state = state
            self.last_transition_time = now
        
        return None
    
    def get_recent_events(self, seconds: int) -> List[MemoryEvent]:
        """Get events from the last n seconds"""
        cutoff = datetime.now() - timedelta(seconds=seconds)
        return [e for e in self.events if e.timestamp >= cutoff]
    
    def get_state_duration(self) -> timedelta:
        """Get how long we've been in the current state"""
        if not self.last_transition_time:
            return timedelta(seconds=0)
        return datetime.now() - self.last_transition_time
    
    def analyze_patterns(self) -> dict:
        """Analyze recent patterns in events"""
        last_minute = self.get_recent_events(60)
        last_5_minutes = self.get_recent_events(300)
        
        return {
            "transitions_last_minute": len([e for e in last_minute if e.event_type == "transition"]),
            "transitions_last_5_minutes": len([e for e in last_5_minutes if e.event_type == "transition"]),
            "current_state_duration": self.get_state_duration().total_seconds()
        } 