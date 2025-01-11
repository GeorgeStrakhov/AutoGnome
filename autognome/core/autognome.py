from datetime import datetime
from pydantic import BaseModel, Field, PrivateAttr
from .config import AutognomeConfig
from ..environment.sensor import EnvironmentSensor, LightLevel

class Autognome(BaseModel):
    """An autognome with energy management and emotional responses"""
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

    def __init__(self, **data):
        if 'energy_level' not in data:
            data['energy_level'] = data.get('config', AutognomeConfig()).initial_energy
        super().__init__(**data)
        self._sensor = EnvironmentSensor()

    def sense_environment(self) -> LightLevel:
        """Read the current light level"""
        return self._sensor.read_light_level()

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
        # First check environment
        light_level = self.sense_environment()
        self.update_emotional_state(light_level)

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
        light_level = self.sense_environment()
        self.update_emotional_state(light_level)
        
        return {
            "time": datetime.now().strftime('%H:%M:%S'),
            "state": "active" if self.decide_action() == "pulse" else "resting",
            "energy": self.energy_level,
            "pulse": self.pulse_count,
            "rest_count": self.rest_count,
            "identifier": self.identifier,
            "name": self.name,
            "light_level": light_level,
            "emotional_state": self.emotional_state
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
        return "..." if light_level == "light" else "*whimper*"  # Different rest response in dark

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
        if light_level == "light":
            return "I pulse boldly in the light!"
        return "I pulse... though it's dark..."  # Less confident in dark

    def act(self) -> str:
        """Perform one action cycle based on current state"""
        action = self.decide_action()
        return self.pulse() if action == "pulse" else self.rest()

    def stop(self) -> None:
        """Stop the autognome's pulsing"""
        self.running = False 