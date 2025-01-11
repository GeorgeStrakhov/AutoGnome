import time
from dataclasses import dataclass, field
import signal
import sys
from datetime import datetime
from pydantic import BaseModel, Field
from typing import ClassVar

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

class Autognome(BaseModel):
    """The simplest possible autognome - a self-asserting pulse"""
    identifier: str = Field(
        ...,  # Required field
        min_length=1, 
        description="Unique identifier for the autognome"
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
    running: bool = Field(
        default=True,
        description="Whether the autognome is currently running"
    )

    def pulse(self) -> str:
        """Generate one pulse of self-assertion"""
        self.pulse_count += 1
        timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] " if self.config.show_timestamp else ""
        return f"{timestamp}I am Autognome-{self.identifier}. I pulse, therefore I am. This is pulse number {self.pulse_count}"
    
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
        autognome = Autognome(identifier="AG1")
        
        while autognome.running:
            print(autognome.pulse())
            time.sleep(autognome.config.pulse_frequency)
    except KeyboardInterrupt:
        print("\nAutognome stopped by user")
    except Exception as e:
        print(f"Failed to start Autognome: {e}")