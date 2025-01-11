import time
import signal
import sys
from autognome.core.autognome import Autognome
from autognome.core.config import AutognomeConfig
from autognome.display.console import ConsoleDisplay

def signal_handler(sig, frame):
    """Handle interrupt signal"""
    print("\nAutognome stopping...")
    sys.exit(0)

def run_autognome(auto: Autognome) -> None:
    """Run an autognome continuously until interrupted"""
    signal.signal(signal.SIGINT, signal_handler)
    display = ConsoleDisplay()
    
    try:
        display.print_startup(auto.name, auto.identifier, auto.config.pulse_frequency)
        display.start()
        
        while auto.running:
            message = auto.act()
            if message != "...":  # Don't add silent pulses to message history
                display.add_message(message)
            display.update(auto.get_status())
            time.sleep(auto.config.pulse_frequency)
            
    except KeyboardInterrupt:
        display.add_message("Stopping...", "system")
        auto.stop()
    except Exception as e:
        display.add_message(f"Error: {e}", "error")
        auto.stop()
        raise
    finally:
        display.stop()

if __name__ == "__main__":
    try:
        autognome = Autognome(
            identifier="4",
            name="Ray",
            config=AutognomeConfig(
                initial_energy=10.0,
                optimal_energy=7.0,
                energy_depletion_rate=1.0,
                energy_recovery_rate=1.0,
                dark_fear_threshold=0.7,
                light_confidence_boost=0.3
            )
        )
        run_autognome(autognome)
    except KeyboardInterrupt:
        print("\nAutognome stopped by user. Goodbye!")
    except Exception as e:
        print(f"Failed to start Autognome: {e}")