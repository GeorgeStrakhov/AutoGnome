"""Environment sensor system for AutoGnomes"""
import os
from pathlib import Path
from typing import Literal

LightLevel = Literal["light", "dark"]

class EnvironmentSensor:
    """Sensor for reading environmental conditions"""
    def __init__(self):
        # Get project root (parent of autognome package)
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.light_sensor_path = self.data_dir / "light_sensor.txt"
        self._ensure_sensor_exists()
    
    def _ensure_sensor_exists(self) -> None:
        """Ensure sensor file exists with default state"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.light_sensor_path.exists():
            self.light_sensor_path.write_text("light")
    
    def read_light_level(self) -> LightLevel:
        """Read the current light level from the sensor"""
        level = self.light_sensor_path.read_text().strip().lower()
        return "light" if level == "light" else "dark"

    def set_light_level(self, level: LightLevel) -> None:
        """Set the light level (for testing/simulation)"""
        self.light_sensor_path.write_text(level) 