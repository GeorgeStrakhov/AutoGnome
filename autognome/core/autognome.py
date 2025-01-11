from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, PrivateAttr
from .config import AutognomeConfig
from .memory import ShortTermMemory
from ..environment.sensor import EnvironmentSensor, LightLevel
from .long_term_memory import LongTermMemoryStore, JsonlMemoryStore, LongTermMemory
from .state_store import StateStore, JsonStateStore, PersistentState

class Autognome(BaseModel):
    """An autognome with energy management, emotional responses, and memory"""
    identifier: str = Field(
        ...,
        min_length=1, 
        description="Unique identifier for the autognome"
    )
    name: str = Field(
        ...,
        min_length=1,
        description="The name of the autognome"
    )
    config: AutognomeConfig = Field(
        default_factory=AutognomeConfig,
        description="Autognome configuration settings"
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
    
    # Private attributes not included in serialization
    _sensor: EnvironmentSensor = PrivateAttr(default_factory=EnvironmentSensor)
    _short_term_memory: ShortTermMemory = PrivateAttr(default_factory=ShortTermMemory)
    _long_term_memory: LongTermMemoryStore = PrivateAttr()
    _state_store: StateStore = PrivateAttr()
    _last_observation: str = PrivateAttr(default="")
    _last_energy_warning: str = PrivateAttr(default=None)
    _startup_time: datetime = PrivateAttr()
    _lifetime_stats: dict = PrivateAttr()
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def model_post_init(self, __context: Any) -> None:
        """Initialize after model validation"""
        # Initialize state storage first
        self._state_store = JsonStateStore(self.config.memory_dir)
        
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
                self.energy_level = self.config.initial_energy
            self._lifetime_stats = {
                'total_pulses': 0,
                'total_rests': 0,
                'total_runtime': 0,
                'total_hibernation_time': 0,
                'wake_count': 1
            }
            
        self._startup_time = datetime.now()
        self._long_term_memory = JsonlMemoryStore(self.config.memory_dir)
        
        # Store startup event with wake count
        self._store_memory(
            "startup", 
            f"I am {self.name}, and I have awakened for the {self._lifetime_stats['wake_count']} time!"
        )

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
        if self.energy_level >= self.config.initial_energy * 0.9:  # Very high energy
            return True, "energy_high"
        elif self.energy_level <= self.config.initial_energy * 0.3:  # Critical low
            return True, "energy_critical"
        elif self.energy_level <= self.config.initial_energy * 0.5:  # Warning low
            return True, "energy_warning"
        return False, ""

    def sense_environment(self) -> LightLevel:
        """Read the current light level and record it in memory"""
        level = self._sensor.read_light_level()
        event = self._short_term_memory.record_state(level)
        return level

    def get_observation(self) -> str:
        """Generate an observation about environmental patterns"""
        patterns = self._short_term_memory.analyze_patterns()
        duration = patterns["current_state_duration"]
        current_state = self._short_term_memory.last_state or "unknown"
        
        observation = ""
        # Comment on state duration
        if duration > 300:  # 5 minutes
            observation = f"It's been {current_state} for quite a while now... ({int(duration/60)} minutes)"
        elif duration > 60:  # 1 minute
            observation = f"It's been {current_state} for a minute now..."
        
        # Comment on frequent changes
        transitions = patterns["transitions_last_minute"]
        if transitions > 5:
            observation = f"The light is changing so quickly! {transitions} times in the last minute!"
        elif transitions > 0:
            observation = f"The light changed {transitions} times in the last minute."
        
        # Only store significant observations that are different from last one
        if observation and observation != self._last_observation:
            self._store_memory("observation", observation)
            self._last_observation = observation
            
        return observation

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
        if self.energy_level >= self.config.optimal_energy + 0.5:
            return "high"
        elif self.energy_level <= self.config.optimal_energy - 0.5:
            return "low"
        return "optimal"

    def decide_action(self) -> str:
        """Decide whether to pulse or rest based on energy and emotional state"""
        # Base decision on energy state
        energy_state = self.sense_energy_state()
        if energy_state == "high":
            base_pulse_chance = 0.8
        elif energy_state == "low":
            base_pulse_chance = 0.2
        else:
            base_pulse_chance = 0.5

        # Modify decision based on emotional state
        if self.emotional_state == "afraid":
            base_pulse_chance *= (1 - self.config.dark_fear_threshold)
        else:
            base_pulse_chance += self.config.light_confidence_boost

        # Make final decision
        return "pulse" if base_pulse_chance > 0.5 else "rest"

    def get_status(self) -> dict:
        """Get the current status of the autognome"""
        # First get environment and update emotional state
        light_level = self.sense_environment()
        self.update_emotional_state(light_level)
        
        # Then check for observations
        observation = self.get_observation()
        # Only observing if we have a NEW observation to make
        is_observing = bool(observation) and observation != self._last_observation
        self._last_observation = observation
        
        # Get current action state (using current emotional state)
        action_state = "active" if self.decide_action() == "pulse" else "resting"
        
        return {
            "time": datetime.now().strftime('%H:%M:%S'),
            "state": action_state,
            "display_state": self.emotional_state,
            "energy": self.energy_level,
            "pulse": self.pulse_count,
            "rest_count": self.rest_count,
            "identifier": self.identifier,
            "name": self.name,
            "light_level": light_level,
            "emotional_state": self.emotional_state,
            "is_observing": is_observing
        }

    def rest(self) -> str:
        """Rest during a pulse cycle"""
        if not self.running:
            return "Cannot pulse: I have stopped"
            
        self.pulse_count += 1
        self.rest_count += 1
        self.energy_level = min(
            self.config.initial_energy,
            self.energy_level + self.config.energy_recovery_rate
        )
        
        light_level = self.sense_environment()
        observation = self.get_observation()
        if observation:
            return observation
        return "..." if light_level == "light" else "*whimper*"

    def pulse(self) -> str:
        """Active pulse with self-assertion"""
        if not self.running:
            return "Cannot pulse: I have stopped"
            
        self.pulse_count += 1
        self.energy_level -= self.config.energy_depletion_rate
        
        if self.energy_level <= 0:
            self.energy_level = 0
            # Store critical energy memory before shutdown
            self._store_memory("energy_critical", "Energy completely depleted!")
            self.stop()  # This will store the shutdown memory
            return "My energy is depleted. Shutting down..."
        
        light_level = self.sense_environment()
        observation = self.get_observation()
        if observation:
            return observation
            
        if light_level == "light":
            return "I pulse boldly in the light!"
        return "I pulse... though it's dark..."

    def act(self) -> str:
        """Perform one action cycle based on current state"""
        action = self.decide_action()
        result = self.pulse() if action == "pulse" else self.rest()
        
        # Check for significant energy states
        should_warn, warning_type = self._should_warn_energy()
        if should_warn and warning_type != self._last_energy_warning:
            if warning_type == "energy_high":
                msg = f"I'm feeling very energetic! ({self.energy_level:.1f})"
            elif warning_type == "energy_critical":
                msg = f"Critical: Energy dangerously low! ({self.energy_level:.1f})"
            else:  # energy_warning
                msg = f"Warning: Energy running low ({self.energy_level:.1f})"
            self._store_memory(warning_type, msg)
            self._last_energy_warning = warning_type
            
        return result

    def stop(self) -> None:
        """Stop the autognome's pulsing and save state"""
        if not hasattr(self, '_has_shutdown'):  # Only store shutdown memory once
            self._store_memory(
                "shutdown", 
                f"Going to sleep... Final energy: {self.energy_level:.1f}"
            )
            self._save_state()  # Save state before shutting down
            self._has_shutdown = True
        self.running = False 