from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import random

@dataclass
class ActionContext:
    """Context provided to the mind for decision making"""
    state: Dict[str, Any]  # Current autognome state
    short_term: List[Dict[str, Any]]  # Recent events/patterns
    long_term: List[Dict[str, Any]]  # Relevant memories
    sensors: Dict[str, Any]  # Current sensor readings
    conversation: List[Dict[str, Any]]  # Recent messages
    last_user_message: Optional[datetime]

@dataclass 
class ActionResult:
    """Result of executing an action"""
    success: bool
    message: str
    metadata: Dict[str, Any]

class Action(Protocol):
    """Base protocol for all actions"""
    async def execute(self, context: ActionContext) -> ActionResult:
        ...
    
    @property
    def display_state(self) -> str:
        """How this action should be displayed in the UI"""
        ...

class Speak(Action):
    """Action to speak a message"""
    def __init__(self, message: str):
        self.message = message
        
    async def execute(self, context: ActionContext) -> ActionResult:
        return ActionResult(
            success=True,
            message=self.message,
            metadata={"type": "speak"}
        )
        
    @property
    def display_state(self) -> str:
        return "speaking"

class Rest(Action):
    """Action to rest and recover energy"""
    def __init__(self, duration: float = 1.0):
        self.duration = duration
        
    async def execute(self, context: ActionContext) -> ActionResult:
        return ActionResult(
            success=True,
            message="...",
            metadata={"type": "rest", "duration": self.duration}
        )
        
    @property
    def display_state(self) -> str:
        return "resting"

class Research(Action):
    """Mock research action"""
    def __init__(self, query: str):
        self.query = query
        
    async def execute(self, context: ActionContext) -> ActionResult:
        # Simulate research taking time
        await asyncio.sleep(random.uniform(0.5, 2.0))
        return ActionResult(
            success=True,
            message=f"I researched: {self.query}",
            metadata={
                "type": "research",
                "query": self.query,
                "results": ["mock result 1", "mock result 2"]
            }
        )
        
    @property
    def display_state(self) -> str:
        return "researching"

class Mind(Protocol):
    """Protocol for mind implementations"""
    async def think(self, context: ActionContext) -> List[Action]:
        """Decide what actions to take"""
        ...
        
    async def reflect(self, context: ActionContext, results: List[ActionResult]) -> None:
        """Process results and update memory/state"""
        ...

class MockMind:
    """A mock mind implementation that simulates different behaviors"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._last_research: Optional[datetime] = None
        
    async def think(self, context: ActionContext) -> List[Action]:
        # Simulate thinking taking time sometimes
        if random.random() < 0.2:  # 20% chance of slow thinking
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
        # If energy is critically low, always rest
        if context.state["energy_level"] <= 2.0:
            return [Rest(duration=2.0)]
            
        # If user just messaged, respond quickly
        if context.last_user_message:
            time_since = (datetime.now() - context.last_user_message).total_seconds()
            if time_since < self.config["conversation"]["wait_for_user"]:
                return [Speak(message="I heard you! Let me think..."), Rest(duration=1.0)]
                
        # Occasionally do research followed by speaking about it
        if (not self._last_research or 
            (datetime.now() - self._last_research).total_seconds() > 30):
            if random.random() < 0.3:  # 30% chance
                self._last_research = datetime.now()
                topics = ["consciousness", "existence", "reality", "time", "space"]
                topic = random.choice(topics)
                return [
                    Research(f"the nature of {topic}"),
                    Speak(f"I've been thinking about {topic}...")
                ]
                
        # Base behavior on emotional state
        if context.state["emotional_state"] == "afraid":
            if random.random() < 0.7:  # 70% chance to express fear
                return [Speak(message="*whimper*")]
            return [Rest(duration=1.0)]  # Otherwise rest
            
        # Default behavior mix
        r = random.random()
        if r < 0.4:  # 40% chance to speak
            messages = [
                "I pulse boldly!",
                "I am aware of my existence!",
                "I wonder about my purpose...",
                "Time flows strangely in my world.",
                "I sense changes around me."
            ]
            return [Speak(message=random.choice(messages))]
        elif r < 0.7:  # 30% chance to rest
            return [Rest(duration=random.uniform(0.5, 1.5))]
        else:  # 30% chance to do nothing
            return []
            
    async def reflect(self, context: ActionContext, results: List[ActionResult]) -> None:
        # Simulate reflection sometimes taking time
        if random.random() < 0.1:  # 10% chance
            await asyncio.sleep(random.uniform(0.5, 1.0)) 