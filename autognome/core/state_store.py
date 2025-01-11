from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json

@dataclass
class PersistentState:
    """Persistent state that survives across sessions"""
    # Current state
    energy_level: float
    emotional_state: str
    last_light_level: str
    last_active: datetime
    last_hibernation: Optional[datetime]
    
    # Lifetime stats
    total_pulses: int
    total_rests: int
    total_runtime: float  # seconds
    total_hibernation_time: float  # seconds
    wake_count: int  # number of times woken up
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersistentState':
        """Create state from dictionary, with datetime parsing"""
        data = data.copy()  # Don't modify original
        data['last_active'] = datetime.fromisoformat(data['last_active'])
        if data['last_hibernation']:
            data['last_hibernation'] = datetime.fromisoformat(data['last_hibernation'])
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary with datetime serialization"""
        data = {
            "energy_level": self.energy_level,
            "emotional_state": self.emotional_state,
            "last_light_level": self.last_light_level,
            "last_active": self.last_active.isoformat(),
            "last_hibernation": self.last_hibernation.isoformat() if self.last_hibernation else None,
            "total_pulses": self.total_pulses,
            "total_rests": self.total_rests,
            "total_runtime": self.total_runtime,
            "total_hibernation_time": self.total_hibernation_time,
            "wake_count": self.wake_count
        }
        return data

class StateStore(ABC):
    """Abstract interface for persistent state storage"""
    
    @abstractmethod
    def save_state(self, state: PersistentState) -> None:
        """Save the current state"""
        pass
    
    @abstractmethod
    def load_state(self) -> Optional[PersistentState]:
        """Load the last saved state if it exists"""
        pass

class JsonStateStore(StateStore):
    """Simple JSON implementation for state persistence"""
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_file = state_dir / "state.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, state: PersistentState) -> None:
        """Save state to JSON file"""
        with open(self.state_file, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)
    
    def load_state(self) -> Optional[PersistentState]:
        """Load state from JSON file if it exists"""
        if not self.state_file.exists():
            return None
            
        try:
            with open(self.state_file) as f:
                data = json.load(f)
            return PersistentState.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None 