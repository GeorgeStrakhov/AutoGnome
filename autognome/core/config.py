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
    energy_recovery_rate: float = Field(
        default=1.0,
        gt=0,
        description="Amount of energy recovered per rest"
    )
    initial_energy: float = Field(
        default=10.0,
        gt=0,
        description="Initial energy level for the autognome"
    )
    optimal_energy: float = Field(
        default=7.0,
        gt=0,
        description="Target energy level for the autognome"
    ) 