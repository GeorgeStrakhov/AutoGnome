from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

@dataclass
class LongTermMemory:
    """A single long-term memory entry"""
    timestamp: datetime
    event_type: str
    state: Dict[str, Any]  # Current autognome state when memory was formed
    observation: str
    emotional_state: str
    context: Dict[str, Any]  # Additional context (e.g., light level, energy)

class LongTermMemoryStore(ABC):
    """Abstract interface for long-term memory storage"""
    
    @abstractmethod
    def store(self, memory: LongTermMemory) -> None:
        """Store a new memory"""
        pass
    
    @abstractmethod
    def search_similar(self, query: str, limit: int = 5) -> List[LongTermMemory]:
        """Find memories similar to the query"""
        pass
    
    @abstractmethod
    def get_recent(self, limit: int = 10) -> List[LongTermMemory]:
        """Get most recent memories"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics for observability"""
        pass
        
    @abstractmethod
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the current session"""
        pass

class JsonlMemoryStore(LongTermMemoryStore):
    """Simple JSONL implementation for initial testing"""
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.memory_file = memory_dir / "memories.jsonl"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
    def store(self, memory: LongTermMemory) -> None:
        """Store a new memory as a JSON line"""
        import json
        memory_dict = {
            "timestamp": memory.timestamp.isoformat(),
            "event_type": memory.event_type,
            "state": memory.state,
            "observation": memory.observation,
            "emotional_state": memory.emotional_state,
            "context": memory.context
        }
        with open(self.memory_file, "a") as f:
            f.write(json.dumps(memory_dict) + "\n")
            
    def search_similar(self, query: str, limit: int = 5) -> List[LongTermMemory]:
        """Basic search implementation - just returns recent memories containing the query"""
        memories = self._read_memories()
        filtered = [m for m in memories if query.lower() in m.observation.lower()]
        return filtered[-limit:]
    
    def get_recent(self, limit: int = 10) -> List[LongTermMemory]:
        """Get most recent memories"""
        memories = self._read_memories()
        return memories[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic memory statistics"""
        memories = self._read_memories()
        if not memories:
            return {"total_memories": 0, "oldest": None, "newest": None}
            
        return {
            "total_memories": len(memories),
            "oldest": memories[0].timestamp.isoformat(),
            "newest": memories[-1].timestamp.isoformat()
        }
        
    def _read_memories(self) -> List[LongTermMemory]:
        """Helper to read all memories from file"""
        import json
        if not self.memory_file.exists():
            return []
            
        memories = []
        with open(self.memory_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    memories.append(LongTermMemory(
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        event_type=data["event_type"],
                        state=data["state"],
                        observation=data["observation"],
                        emotional_state=data["emotional_state"],
                        context=data["context"]
                    ))
        return sorted(memories, key=lambda x: x.timestamp) 
        
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the current session"""
        memories = self._read_memories()
        if not memories:
            return {"error": "No memories found"}
            
        # Find the startup event for this session
        startup_memories = [m for m in memories if m.event_type == "startup"]
        if not startup_memories:
            return {"error": "No startup event found"}
            
        # Get the most recent startup
        session_start = startup_memories[-1]
        session_start_time = session_start.timestamp
        
        # Filter memories for this session
        session_memories = [m for m in memories if m.timestamp >= session_start_time]
        
        # Count different types of events
        event_counts = {}
        for memory in session_memories:
            event_counts[memory.event_type] = event_counts.get(memory.event_type, 0) + 1
            
        # Calculate session duration
        if session_memories[-1].event_type == "shutdown":
            end_time = session_memories[-1].timestamp
        else:
            end_time = datetime.now()
        duration = end_time - session_start_time
        
        # Get final state from last memory
        final_state = session_memories[-1].state
        
        return {
            "session_duration": duration.total_seconds(),
            "total_memories": len(session_memories),
            "event_counts": event_counts,
            "final_state": final_state,
            "start_time": session_start_time.isoformat(),
            "end_time": end_time.isoformat()
        } 