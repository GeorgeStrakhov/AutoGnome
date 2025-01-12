from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, PrivateAttr
import asyncio
import logging

from .loader import AutognomeConfig
from .memory import ShortTermMemory
from ..environment.sensor import EnvironmentSensor, LightLevel
from .long_term_memory import LongTermMemoryStore, JsonlMemoryStore, LongTermMemory
from .state_store import StateStore, JsonStateStore, PersistentState
from .mind import MockMind, ActionContext, Action, ActionResult, Rest

logger = logging.getLogger(__name__)

class Autognome(BaseModel):
    """An autognome with energy management, emotional responses, and memory"""
    config: AutognomeConfig = Field(
        ...,
        description="Loaded configuration for this autognome"
    )
    pulse_count: int = Field(
        default=0, 
        ge=0,
        description="Number of pulses in current session"
    )
    rest_count: int = Field(
        default=0,
        ge=0,
        description="Number of rests in current session"
    )
    energy_level: float = Field(
        default=None,
        ge=0,
        description="Current energy level"
    )
    running: bool = Field(
        default=True,
        description="Whether the autognome is currently running"
    )
    emotional_state: str = Field(
        default="normal",
        description="Current emotional state"
    )
    mind_state: str = Field(
        default="idle",
        description="Current state of the mind"
    )
    remaining_rest_pulses: int = Field(
        default=0,
        ge=0,
        description="Number of pulses left to rest"
    )
    
    # Private attributes not included in serialization
    _sensor: EnvironmentSensor = PrivateAttr(default_factory=EnvironmentSensor)
    _short_term_memory: ShortTermMemory = PrivateAttr()
    _long_term_memory: LongTermMemoryStore = PrivateAttr()
    _state_store: StateStore = PrivateAttr()
    _last_observation: str = PrivateAttr(default="")
    _last_energy_warning: str = PrivateAttr(default=None)
    _startup_time: datetime = PrivateAttr()
    _lifetime_stats: dict = PrivateAttr()
    _base_dir: Path = PrivateAttr()
    _mind: Any = PrivateAttr()  # Will be Mind protocol
    _last_user_message: Optional[datetime] = PrivateAttr(default=None)
    _conversation_history: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _current_actions: List[Action] = PrivateAttr(default_factory=list)
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def model_post_init(self, __context: Any) -> None:
        """Initialize after model validation"""
        # Set up base directory for this AG
        self._base_dir = Path("data/autognomes") / self.config.version
        
        # Initialize memory with configured capacity
        self._short_term_memory = ShortTermMemory(
            capacity=self.config.memory["short_term_capacity"]
        )
        
        # Initialize state storage with full paths
        self._state_store = JsonStateStore(self._base_dir)
        self._long_term_memory = JsonlMemoryStore(self._base_dir)
        
        # Initialize mind based on config
        if self.config.mind["type"] == "mock":
            self._mind = MockMind(self.config.mind)
        else:
            raise ValueError(f"Unknown mind type: {self.config.mind['type']}")
        
        # Try to load previous state
        prev_state = self._state_store.load_state()
        if prev_state:
            # Calculate hibernation time
            now = datetime.now()
            hibernation_time = (now - prev_state.last_active).total_seconds()
            
            # Initialize with previous state
            self.energy_level = prev_state.energy_level
            self.emotional_state = prev_state.emotional_state
            self._lifetime_stats = {
                'total_pulses': prev_state.total_pulses,
                'total_rests': prev_state.total_rests,
                'total_runtime': prev_state.total_runtime,
                'total_hibernation_time': prev_state.total_hibernation_time + hibernation_time,
                'wake_count': prev_state.wake_count + 1
            }
        else:
            # Initialize fresh state
            if self.energy_level is None:
                self.energy_level = self.config.core["initial_energy"]
            self._lifetime_stats = {
                'total_pulses': 0,
                'total_rests': 0,
                'total_runtime': 0,
                'total_hibernation_time': 0,
                'wake_count': 1
            }
            
        self._startup_time = datetime.now()
        
        # Store startup event with wake count
        self._store_memory(
            "startup", 
            f"I am {self.config.name}, and I have awakened for the {self._lifetime_stats['wake_count']} time!"
        )
        
        # Save initial state
        self._save_state()

    def _build_context(self) -> ActionContext:
        """Build context for mind operations"""
        return ActionContext(
            state={
                "energy_level": self.energy_level,
                "emotional_state": self.emotional_state,
                "pulse_count": self.pulse_count,
                "rest_count": self.rest_count,
                "running": self.running,
                "energy_state": self.sense_energy_state()
            },
            short_term=self._short_term_memory.analyze_patterns(),
            long_term=self._long_term_memory.get_recent(5),
            sensors={
                "light": self._sensor.read_light_level()
            },
            conversation=self._conversation_history[-10:],  # Last 10 messages
            last_user_message=self._last_user_message
        )

    def _process_observation(self, had_transition: bool = False) -> Optional[str]:
        """Centralized observation processing.
        Returns a message if there's a new observation to report."""
        observation = None
        
        # First check transition-based observations
        if had_transition:
            patterns = self._short_term_memory.analyze_patterns()
            transitions = patterns["transitions_last_minute"]
            if transitions > 5:
                observation = f"The light is changing so quickly! {transitions} times in the last minute!"
            elif transitions > 0:
                observation = f"The light changed {transitions} times in the last minute."
        
        # Then check time-based observations
        if not observation:  # Only if we don't have a transition observation
            patterns = self._short_term_memory.analyze_patterns()
            duration = patterns["current_state_duration"]
            current_state = self._short_term_memory.last_state or "unknown"
            
            if 59 < duration < 61:  # Just reached 1 minute
                observation = f"It's been {current_state} for a minute now..."
            elif 299 < duration < 301:  # Just reached 5 minutes
                observation = f"It's been {current_state} for quite a while now... ({int(duration/60)} minutes)"
        
        # Store and return if we have a new observation
        if observation and observation != self._last_observation:
            self._store_memory("observation", observation)
            self._last_observation = observation
            return observation
            
        return None

    async def act(self) -> Optional[str]:
        """Perform one pulse of activity."""
        # Increment pulse count at start of each pulse
        self.pulse_count += 1
        
        # If we're still resting, continue resting
        if self.remaining_rest_pulses > 0:
            self._recover_energy()
            self.remaining_rest_pulses -= 1
            self.mind_state = "resting"
            return None

        # Build context for mind
        context = self._build_context()
        
        # Think and get actions
        try:
            actions = await self._mind.think(context)
            self.mind_state = "acting"
            self._current_actions = actions
            
            # Execute actions
            message = None
            for action in actions:
                result = await action.execute(context)
                if not result.success:
                    logger.error(f"Action failed: {result.message}")
                    continue
                    
                # Handle rest actions specially
                if isinstance(action, Rest):
                    self.remaining_rest_pulses = action.pulses - 1  # -1 since we're using this pulse
                    self._recover_energy()
                    self.mind_state = "resting"
                    self.rest_count += 1  # Increment rest count
                    return "Taking a rest..."
                
                # Store messages from speak actions
                if result.metadata.get("type") == "speak":
                    message = result.message
                    self._conversation_history.append({
                        "role": "assistant",
                        "content": message,
                        "timestamp": datetime.now()
                    })
                    
            # Reflect on actions
            try:
                await self._mind.reflect(context, actions)
            except Exception as e:
                logger.exception("Error in mind reflection")
                # Don't change mind state or return error - just log it
            
            return message
            
        except Exception as e:
            logger.exception("Error in mind processing")
            self.mind_state = "error"
            return f"Error: {str(e)}"
            
        # If we got here, we did work this pulse
        self._deplete_energy()
        self._save_state()

    def record_user_message(self, message: str) -> None:
        """Record a message from the user"""
        self._last_user_message = datetime.now()
        self._conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": self._last_user_message
        })

    def get_status(self) -> dict:
        """Get the current status of the autognome"""
        # First get environment and update emotional state
        light_level, had_transition = self.sense_environment()
        self.update_emotional_state(light_level)
        
        # Process any observations
        observation = self._process_observation(had_transition)
        is_observing = bool(observation)
        
        return {
            "time": datetime.now().strftime('%H:%M:%S'),
            "state": "active",
            "display_state": self.emotional_state,
            "energy": self.energy_level,
            "pulse": self.pulse_count,
            "rest_count": self.rest_count,
            "identifier": self.config.version,
            "name": self.config.name,
            "light_level": light_level,
            "emotional_state": self.emotional_state,
            "is_observing": is_observing,
            "mind_state": self.mind_state,
            "ascii_art": self._get_ascii_art(is_observing),
            "observation": observation  # Include any observation message
        }

    def _get_ascii_art(self, is_observing: bool) -> str:
        """Get appropriate ASCII art based on state"""
        ascii_art = self.config.display["ascii_art"]
        if not self.running:
            art_key = "sleeping"
        elif is_observing or self.mind_state in ["thinking", "researching"]:
            art_key = "thinking"
        else:
            art_key = self.emotional_state
            
        art_path = self._base_dir / ascii_art[art_key]
        try:
            with open(art_path) as f:
                return f.read()
        except Exception as e:
            return f"Error loading ASCII art: {e}"

    def _save_state(self) -> None:
        """Save current state to persistent storage"""
        now = datetime.now()
        runtime = (now - self._startup_time).total_seconds()
        
        state = PersistentState(
            energy_level=self.energy_level,
            emotional_state=self.emotional_state,
            last_light_level=self._sensor.read_light_level(),
            last_active=now,
            last_hibernation=now if not self.running else None,
            total_pulses=self._lifetime_stats['total_pulses'] + self.pulse_count,
            total_rests=self._lifetime_stats['total_rests'] + self.rest_count,
            total_runtime=self._lifetime_stats['total_runtime'] + runtime,
            total_hibernation_time=self._lifetime_stats['total_hibernation_time'],
            wake_count=self._lifetime_stats['wake_count']
        )
        self._state_store.save_state(state)

    def get_lifetime_stats(self) -> dict:
        """Get the current lifetime statistics"""
        now = datetime.now()
        runtime = (now - self._startup_time).total_seconds()
        
        return {
            'total_pulses': self._lifetime_stats['total_pulses'] + self.pulse_count,
            'total_rests': self._lifetime_stats['total_rests'] + self.rest_count,
            'total_runtime': self._lifetime_stats['total_runtime'] + runtime,
            'total_hibernation_time': self._lifetime_stats['total_hibernation_time'],
            'wake_count': self._lifetime_stats['wake_count'],
            'current_session_runtime': runtime
        }

    def _should_warn_energy(self) -> tuple[bool, str]:
        """Determine if we should store an energy-related memory"""
        initial = self.config.core["initial_energy"]
        if self.energy_level >= initial * 0.9:  # Very high energy
            return True, "energy_high"
        elif self.energy_level <= initial * 0.3:  # Critical low
            return True, "energy_critical"
        elif self.energy_level <= initial * 0.5:  # Warning low
            return True, "energy_warning"
        return False, ""

    def sense_environment(self) -> tuple[LightLevel, bool]:
        """Read the current light level and record it in memory.
        Returns (level, had_transition)"""
        level = self._sensor.read_light_level()
        # Record state with more details
        event = self._short_term_memory.record_state(
            level,
            f"Light level is {level} at energy {self.energy_level:.1f}"
        )
        # If there was a transition, store it in long-term memory too
        if event:
            self._store_memory("light_change", event.details)
        return level, bool(event)

    def _store_memory(self, event_type: str, observation: str) -> None:
        """Store a new long-term memory"""
        from datetime import datetime
        
        # During shutdown, don't try to read sensors
        if event_type == "shutdown":
            light_level = "unknown"
            energy_state = "shutdown"
        else:
            light_level = self._sensor.read_light_level()
            energy_state = self.sense_energy_state()
            
        memory = LongTermMemory(
            timestamp=datetime.now(),
            event_type=event_type,
            state={
                "energy_level": self.energy_level,
                "pulse_count": self.pulse_count,
                "rest_count": self.rest_count,
                "running": self.running
            },
            observation=observation,
            emotional_state=self.emotional_state,
            context={
                "light_level": light_level,
                "energy_state": energy_state
            }
        )
        self._long_term_memory.store(memory)

    def update_emotional_state(self, light_level: LightLevel) -> None:
        """Update emotional state based on environment"""
        new_state = "normal" if light_level == "light" else "afraid"
        if new_state != self.emotional_state:
            self._store_memory(
                "emotional_change",
                f"I'm feeling {new_state} now... (was {self.emotional_state})"
            )
            self.emotional_state = new_state

    def sense_energy_state(self) -> str:
        """Determine current energy state relative to optimal"""
        optimal = self.config.core["optimal_energy"]
        if self.energy_level >= optimal + 0.5:
            return "high"
        elif self.energy_level <= optimal - 0.5:
            return "low"
        return "optimal"

    def stop(self) -> None:
        """Stop the autognome's pulsing and save state"""
        if not hasattr(self, '_has_shutdown'):  # Only store shutdown memory once
            self._store_memory(
                "shutdown", 
                f"Going to sleep... Final energy: {self.energy_level:.1f}"
            )
            self._save_state()  # Save state before shutting down
            self.mind_state = "sleeping"
            self._has_shutdown = True
        self.running = False 

    def _recover_energy(self) -> None:
        """Recover energy during rest."""
        recovery = self.config.core["energy_recovery_rate"]
        max_energy = self.config.core["optimal_energy"] * 1.5
        self.energy_level = min(
            self.energy_level + recovery,
            max_energy
        )
        
    def _deplete_energy(self) -> None:
        """Deplete energy when doing work."""
        self.energy_level = max(
            0.0,
            self.energy_level - self.config.core["energy_depletion_rate"]
        ) 