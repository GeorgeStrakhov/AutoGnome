from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
from pathlib import Path
from typing import Optional, Dict
from ..core.autognome import Autognome
from ..core.loader import AutognomeLoader

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Store current autognome instance in app state
app.state.current_autognome: Optional[Autognome] = None
app.state.websocket: Optional[WebSocket] = None
app.state.ascii_art_cache: Dict[str, str] = {}  # Cache for ASCII art

def load_ascii_art(art_path: str, base_dir: Path) -> str:
    """Load ASCII art from file, using cache if available"""
    cache_key = str(base_dir / art_path)
    if cache_key in app.state.ascii_art_cache:
        return app.state.ascii_art_cache[cache_key]
        
    try:
        with open(base_dir / art_path) as f:
            art = f.read()
            app.state.ascii_art_cache[cache_key] = art
            return art
    except Exception as e:
        print(f"Error loading ASCII art from {art_path}: {e}")
        return "ERROR: Could not load ASCII art"

@app.get("/")
async def get_index():
    """Serve the index.html file"""
    return FileResponse(Path(__file__).parent / "static" / "index.html")

@app.get("/api/versions")
async def get_versions():
    """Get available AG versions"""
    loader = AutognomeLoader()
    versions = []
    for version in loader.get_available_versions():
        config = loader.load_config(version)
        if config:
            versions.append({
                "id": version,
                "name": config.name,
                "description": config.description
            })
    return {"versions": versions}

@app.post("/api/start/{version}")
async def start_autognome(version: str):
    """Start a new autognome instance"""
    loader = AutognomeLoader()
    config = loader.create_instance(version)
    if not config:
        return {"error": f"Version {version} not found"}
        
    app.state.current_autognome = Autognome(config=config)
    # Clear ASCII art cache on new instance
    app.state.ascii_art_cache.clear()
    return {"status": "ok"}

@app.on_event("shutdown")
async def shutdown_event():
    """Handle graceful shutdown"""
    if app.state.current_autognome:
        app.state.current_autognome.stop()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await websocket.accept()
    app.state.websocket = websocket
    
    try:
        while True:
            # Handle incoming messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                # Handle commands
                if data == "toggle_light":
                    # Light can be toggled even when AG is sleeping
                    current = app.state.current_autognome._sensor.read_light_level()
                    new_level = "dark" if current == "light" else "light"
                    app.state.current_autognome._sensor.set_light_level(new_level)
                    await websocket.send_json({
                        "type": "message",
                        "data": f"Light level changed to {new_level}."
                    })
                elif data == "rest":
                    if app.state.current_autognome.running:
                        app.state.current_autognome.start_rest()
                    else:
                        await websocket.send_json({
                            "type": "message",
                            "data": "I'm sleeping right now. Use 'wake' to wake me up first."
                        })
                elif data == "sleep":
                    if app.state.current_autognome.running:
                        app.state.current_autognome.stop()
                        await websocket.send_json({
                            "type": "message",
                            "data": "Going to sleep... Goodnight!"
                        })
                    else:
                        await websocket.send_json({
                            "type": "message",
                            "data": "I'm already sleeping."
                        })
                elif data == "wake":
                    if not app.state.current_autognome.running:
                        app.state.current_autognome.running = True
                        await websocket.send_json({
                            "type": "message",
                            "data": "Good morning! I'm awake now."
                        })
                    else:
                        await websocket.send_json({
                            "type": "message",
                            "data": "I'm already awake!"
                        })
                # Handle chat messages
                elif data.startswith("hello"):
                    state = "sleeping" if not app.state.current_autognome.running else "awake"
                    await websocket.send_json({
                        "type": "message",
                        "data": f"Hello! I am {app.state.current_autognome.config.name}, AG-{app.state.current_autognome.config.version}. I am currently {state}."
                    })
                elif data == "help":
                    help_text = """Available commands:
• hello - Get a greeting from me
• status - Get my current status
• rest - Tell me to take a rest
• toggle_light - Toggle the light level
• sleep - Tell me to go to sleep
• wake - Wake me up from sleep
• help - Show this help message"""
                    await websocket.send_json({
                        "type": "message",
                        "data": help_text
                    })
                elif data == "status":
                    energy = app.state.current_autognome.energy_level
                    if app.state.current_autognome.running:
                        state = "resting" if app.state.current_autognome.is_resting else "active"
                    else:
                        state = "sleeping"
                    await websocket.send_json({
                        "type": "message",
                        "data": f"I am {state} with {energy:.1f} energy."
                    })
            except asyncio.TimeoutError:
                pass  # No message received, continue with status updates
                
            # Send status updates
            if app.state.current_autognome:
                # Get base status (even when sleeping)
                status = app.state.current_autognome.get_status()
                
                # Only do actions and get messages if running
                if app.state.current_autognome.running:
                    message = app.state.current_autognome.act()
                    # Add message to status if it's meaningful
                    if message and message not in ["...", "*whimper*"]:
                        await websocket.send_json({
                            "type": "message",
                            "data": message
                        })
                
                # Add ASCII art from files based on state
                auto = app.state.current_autognome
                ascii_art = auto.config.display["ascii_art"]
                base_dir = Path("data/autognomes") / auto.config.version
                
                if status["is_observing"]:
                    status["ascii_art"] = load_ascii_art(ascii_art["thinking"], base_dir)
                else:
                    status["ascii_art"] = load_ascii_art(ascii_art[status["emotional_state"]], base_dir)
                    
                # Send status update
                await websocket.send_json({
                    "type": "status",
                    "data": status
                })
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        app.state.websocket = None

@app.post("/api/command/{cmd}")
async def handle_command(cmd: str):
    """Handle commands from the web interface"""
    if not app.state.current_autognome:
        return {"error": "No autognome running"}
        
    if cmd == "rest":
        app.state.current_autognome.start_rest()
    elif cmd == "sleep":
        app.state.current_autognome.stop()
    elif cmd == "wake":
        app.state.current_autognome.running = True
    elif cmd == "toggle_light":
        # Toggle the light level in the sensor
        current = app.state.current_autognome._sensor.read_light_level()
        new_level = "dark" if current == "light" else "light"
        app.state.current_autognome._sensor.set_light_level(new_level)
        
    return {"status": "ok"} 