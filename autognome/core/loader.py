from pathlib import Path
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
from litellm import supports_function_calling

@dataclass
class AutognomeConfig:
    """Configuration loaded from YAML"""
    version: str
    name: str
    description: str
    core: Dict[str, float]
    personality: Dict[str, Any]
    memory: Dict[str, Any]
    display: Dict[str, Any]
    sensors: List[Dict[str, Any]]
    mind: Dict[str, Any]

class AutognomeLoader:
    """Loads autognome configurations from YAML files"""
    
    def __init__(self, data_dir: Path = Path("data/autognomes")):
        self.data_dir = data_dir
        
    def get_available_versions(self) -> list[str]:
        """Get list of available AG versions"""
        return [d.name for d in self.data_dir.iterdir() if d.is_dir()]
        
    @staticmethod
    def load_config(version: str) -> AutognomeConfig:
        """Load configuration for the specified version"""
        config_path = Path("data/autognomes") / version / "ag.yaml"
        
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                
            # Check if using LLM and validate function call support
            if config_data.get("mind", {}).get("type") == "llm":
                model = config_data["mind"]["model"]
                if not supports_function_calling(model):
                    raise ValueError(
                        f"Model {model} does not support function calling. "
                        "Please use a model that supports function calling or use mock mind type."
                    )
                
            return AutognomeConfig(**config_data)
            
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return None
        
    def get_state_path(self, version: str) -> Path:
        """Get path to state file for version"""
        return self.data_dir / version / "state.json"
        
    def get_memory_path(self, version: str) -> Path:
        """Get path to memory file for version"""
        return self.data_dir / version / "memories.jsonl"
        
    def create_instance(self, version: str) -> Optional[AutognomeConfig]:
        """Create a new instance of an AG version"""
        config = self.load_config(version)
        if not config:
            return None
            
        # Ensure version directory exists
        version_dir = self.data_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Create empty state and memory files if they don't exist
        state_path = self.get_state_path(version)
        memory_path = self.get_memory_path(version)
        
        if not state_path.exists():
            state_path.write_text("{}")
        if not memory_path.exists():
            memory_path.touch()
            
        return config 