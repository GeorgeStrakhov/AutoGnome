import time
import signal
import sys
from datetime import timedelta
from autognome.core.autognome import Autognome
from autognome.core.config import AutognomeConfig
from autognome.display.console import ConsoleDisplay

def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human readable string"""
    duration = timedelta(seconds=seconds)
    parts = []
    days = duration.days
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60
    
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)

def display_session_summary(auto: Autognome) -> None:
    """Display a summary of the session"""
    summary = auto._long_term_memory.get_session_summary()
    if "error" in summary:
        print(f"\nSession summary error: {summary['error']}")
        return
        
    lifetime = auto.get_lifetime_stats()
    
    print("\n=== Session Summary ===")
    print(f"Duration: {format_duration(summary['session_duration'])}")
    print(f"Total memories formed: {summary['total_memories']}")
    
    print("\nMemory breakdown:")
    for event_type, count in summary['event_counts'].items():
        print(f"  {event_type}: {count}")
    
    final_state = summary['final_state']
    print("\nSession state:")
    print(f"  Energy level: {final_state['energy_level']:.1f}")
    print(f"  Session pulses: {final_state['pulse_count']}")
    print(f"  Session rests: {final_state['rest_count']}")
    
    print("\nLifetime Statistics:")
    print(f"  Total wake cycles: {lifetime['wake_count']}")
    print(f"  Total runtime: {format_duration(lifetime['total_runtime'])}")
    print(f"  Total hibernation: {format_duration(lifetime['total_hibernation_time'])}")
    print(f"  Total pulses: {lifetime['total_pulses']}")
    print(f"  Total rests: {lifetime['total_rests']}")
    print("===================")

def run_autognome(auto: Autognome) -> None:
    """Run an autognome continuously until interrupted"""
    display = ConsoleDisplay()
    
    def handle_interrupt(sig, frame):
        """Handle interrupt signal by stopping the autognome"""
        print("\nReceived shutdown signal...")
        display.add_message("Preparing for hibernation...", "system")
        auto.stop()  # Call stop directly
    
    # Set up signal handler
    signal.signal(signal.SIGINT, handle_interrupt)
    
    try:
        display.print_startup(auto.name, auto.identifier, auto.config.pulse_frequency)
        display.start()
        
        while auto.running:
            message = auto.act()
            if message != "...":  # Don't add silent pulses to message history
                display.add_message(message)
            display.update(auto.get_status())
            time.sleep(auto.config.pulse_frequency)
            
    except Exception as e:
        display.add_message(f"Error: {e}", "error")
        auto.stop()
        raise
    finally:
        display.stop()

if __name__ == "__main__":
    autognome = None
    try:
        autognome = Autognome(
            identifier="7",  # AG7
            name="Chronos the Constant",  # Emphasizes continuous existence through time
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
    except Exception as e:
        print(f"\nFailed to start/run Autognome: {e}")
    finally:
        if autognome:
            # Ensure we're stopped before displaying summary
            if autognome.running:
                autognome.stop()
            display_session_summary(autognome)
            print("\nHibernation complete. Goodbye!")