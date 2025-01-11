from datetime import datetime
from pydantic import BaseModel, Field, PrivateAttr
from .config import AutognomeConfig
from .memory import ShortTermMemory
from ..environment.sensor import EnvironmentSensor, LightLevel

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
        description="Number of pulses emitted"
    )
    rest_count: int = Field(
        default=0,
        ge=0,
        description="Number of times rested"
    )
    energy_level: float = Field(
        ...,
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
    _sensor: EnvironmentSensor = PrivateAttr()
    _memory: ShortTermMemory = PrivateAttr()
    _last_observation: str = PrivateAttr(default="")

    def __init__(self, **data):
        if 'energy_level' not in data:
            data['energy_level'] = data.get('config', AutognomeConfig()).initial_energy
        super().__init__(**data)
        self._sensor = EnvironmentSensor()
        self._memory = ShortTermMemory()

    def sense_environment(self) -> LightLevel:
        """Read the current light level and record it in memory"""
        level = self._sensor.read_light_level()
        event = self._memory.record_state(level)
        return level

    def get_observation(self) -> str:
        """Generate an observation about environmental patterns"""
        patterns = self._memory.analyze_patterns()
        duration = patterns["current_state_duration"]
        current_state = self._memory.last_state or "unknown"
        
        # Comment on state duration
        if duration > 300:  # 5 minutes
            return f"It's been {current_state} for quite a while now... ({int(duration/60)} minutes)"
        elif duration > 60:  # 1 minute
            return f"It's been {current_state} for a minute now..."
        
        # Comment on frequent changes
        transitions = patterns["transitions_last_minute"]
        if transitions > 5:
            return f"The light is changing so quickly! {transitions} times in the last minute!"
        elif transitions > 0:
            return f"The light changed {transitions} times in the last minute."
            
        return ""  # No notable patterns to comment on

    def update_emotional_state(self, light_level: LightLevel) -> None:
        """Update emotional state based on environment"""
        self.emotional_state = "normal" if light_level == "light" else "afraid"

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
            self.stop()
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
        return self.pulse() if action == "pulse" else self.rest()

    def stop(self) -> None:
        """Stop the autognome's pulsing"""
        self.running = False 