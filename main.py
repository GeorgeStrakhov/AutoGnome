import time
import signal
import sys
from datetime import datetime
from pydantic import BaseModel, Field

class AutognomeConfig(BaseModel):
    """Configuration for an autognome"""
    pulse_frequency: float = Field(
        default=1.0, 
        gt=0, 
        description="Seconds between pulses"
    )
    show_timestamp: bool = Field(
        default=True, 
        description="Whether to show timestamp in pulses"
    )
    energy_depletion_rate: float = Field(
        default=1.0,
        gt=0,
        description="Amount of energy depleted per pulse"
    )
    initial_energy: float = Field(
        default=10.0,
        gt=0,
        description="Initial energy level for the autognome"
    )

class Autognome(BaseModel):
    """An autognome with energy level and name"""
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

    def pulse(self) -> str:
        """Generate one pulse of self-assertion and deplete energy"""
        if not self.running:
            return f"Cannot pulse: {self.name} has stopped"
            
        self.pulse_count += 1
        self.energy_level -= self.config.energy_depletion_rate
        
        if self.energy_level <= 0:
            self.energy_level = 0
            self.stop()
            message = f"I am {self.name} (AG-{self.identifier}). My energy is depleted. Shutting down..."
        else:
            timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] " if self.config.show_timestamp else ""
            message = f"{timestamp}I am {self.name} (AG-{self.identifier}). Energy level: {self.energy_level:.1f}. This is pulse number {self.pulse_count}"
        
        return message
    
    def stop(self) -> None:
        """Stop the autognome's pulsing"""
        self.running = False

def signal_handler(sig, frame):
    """Handle interrupt signal"""
    print("\nAutognome stopping...")
    sys.exit(0)

def run_autognome(auto: Autognome) -> None:
    """Run an autognome continuously until interrupted"""
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print(f"Starting Autognome-{auto.identifier}...")
        print(f"Pulse frequency: {auto.config.pulse_frequency} seconds")
        print("-" * 50)
        
        while auto.running:
            print(auto.pulse())
            time.sleep(auto.config.pulse_frequency)
    except KeyboardInterrupt:
        print("\nAutognome stopping...")
        auto.stop()
    except Exception as e:
        print(f"\nError occurred: {e}")
        auto.stop()
        raise

if __name__ == "__main__":
    try:
        autognome = Autognome(
            identifier="AG2",
            name="Energetic Eddie",
            config=AutognomeConfig(initial_energy=10.0)
        )
        
        while autognome.running:
            print(autognome.pulse())
            time.sleep(autognome.config.pulse_frequency)
    except KeyboardInterrupt:
        print("\nAutognome stopped by user")
    except Exception as e:
        print(f"Failed to start Autognome: {e}")