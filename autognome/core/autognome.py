from datetime import datetime
from pydantic import BaseModel, Field
from .config import AutognomeConfig

class Autognome(BaseModel):
    """An autognome with energy management and decision making"""
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

    def __init__(self, **data):
        if 'energy_level' not in data:
            data['energy_level'] = data.get('config', AutognomeConfig()).initial_energy
        super().__init__(**data)

    def sense_energy_state(self) -> str:
        """Determine current energy state relative to optimal"""
        if self.energy_level >= self.config.optimal_energy + 0.5:
            return "high"
        elif self.energy_level <= self.config.optimal_energy - 0.5:
            return "low"
        return "optimal"

    def decide_action(self) -> str:
        """Decide whether to pulse or rest based on energy state"""
        energy_state = self.sense_energy_state()
        if energy_state == "high":
            return "pulse"
        elif energy_state == "low":
            return "rest"
        # At optimal energy, bias towards resting if energy is below optimal
        if self.energy_level < self.config.optimal_energy:
            return "rest"
        return "pulse"

    def get_status(self) -> dict:
        """Get the current status of the autognome"""
        return {
            "time": datetime.now().strftime('%H:%M:%S'),
            "state": "active" if self.decide_action() == "pulse" else "resting",
            "energy": self.energy_level,
            "pulse": self.pulse_count,
            "rest_count": self.rest_count,
            "identifier": self.identifier,
            "name": self.name
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
        
        return "..." # Silent pulse

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
        
        return "I pulse, therefore I am."

    def act(self) -> str:
        """Perform one action cycle based on current state"""
        action = self.decide_action()
        return self.pulse() if action == "pulse" else self.rest()

    def stop(self) -> None:
        """Stop the autognome's pulsing"""
        self.running = False 