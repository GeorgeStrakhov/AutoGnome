import uvicorn
import signal
import sys
import webbrowser
import threading
import time
from datetime import timedelta
from autognome.web.server import app
from autognome.core.loader import AutognomeLoader
from autognome.core.autognome import Autognome

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

def display_session_summary(auto) -> None:
    """Display a summary of the session"""
    if not auto:
        return
        
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

def handle_shutdown(signum, frame):
    """Handle shutdown signal"""
    print("\nShutting down...")
    # Get current autognome instance
    auto = app.state.current_autognome
    if auto:
        # First stop the autognome (this will store shutdown memory)
        auto.stop()
        # Then display summary
        display_session_summary(auto)
        print("\nHibernation complete. Goodbye!")
    sys.exit(0)

def open_browser():
    """Open browser after a short delay to ensure server is running"""
    time.sleep(1.5)  # Wait for server to start
    webbrowser.open("http://127.0.0.1:8000")

def select_autognome() -> str:
    """Interactive selection of which AG to run"""
    loader = AutognomeLoader()
    versions = loader.get_available_versions()
    if not versions:
        print("No AG versions found in data/autognomes/")
        sys.exit(1)
        
    print("\nAvailable AutoGnomes:")
    for i, version in enumerate(versions, 1):
        config = loader.load_config(version)
        if config:
            print(f"\n{i}. {config.name} ({version})")
            print(f"   {config.description.split('\n')[0]}")
    print()
    
    while True:
        try:
            choice = input("Select an AutoGnome to run (1-%d): " % len(versions))
            idx = int(choice) - 1
            if 0 <= idx < len(versions):
                selected = versions[idx]
                print(f"\nStarting {selected}...")
                return selected
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")

if __name__ == "__main__":
    # Select which AG to run
    version = select_autognome()
    
    # Initialize the selected AG
    loader = AutognomeLoader()
    config = loader.create_instance(version)
    if not config:
        print(f"Failed to start {version}")
        sys.exit(1)
    app.state.current_autognome = Autognome(config=config)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the server with graceful shutdown
    config = uvicorn.Config(app, host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    server.run()