from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
from loguru import logger
from pathlib import Path
from typing import Optional, Dict
from ..core.autognome import Autognome
from ..core.loader import AutognomeLoader
from ..core.mind import Speak, Rest
import random

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Store current autognome instance in app state
app.state.current_autognome: Optional[Autognome] = None
app.state.websocket: Optional[WebSocket] = None
app.state.ascii_art_cache: Dict[str, str] = {}  # Cache for ASCII art
app.state.pulse_task: Optional[asyncio.Task] = None

@app.on_event("startup")
async def startup_event():
    """Start the pulse loop when the server starts"""
    if app.state.current_autognome:
        app.state.pulse_task = asyncio.create_task(pulse_loop())

@app.on_event("shutdown")
async def shutdown_event():
    """Handle graceful shutdown"""
    if app.state.pulse_task:
        app.state.pulse_task.cancel()
        try:
            await app.state.pulse_task
        except asyncio.CancelledError:
            pass
            
    if app.state.current_autognome:
        app.state.current_autognome.stop()

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
        
    # Stop existing pulse task if any
    if app.state.pulse_task:
        app.state.pulse_task.cancel()
        try:
            await app.state.pulse_task
        except asyncio.CancelledError:
            pass
            
    app.state.current_autognome = Autognome(config=config)
    # Clear ASCII art cache on new instance
    app.state.ascii_art_cache.clear()
    
    # Start pulse task
    app.state.pulse_task = asyncio.create_task(pulse_loop())
    return {"status": "ok"}

async def pulse_loop():
    """Main pulse loop for the autognome"""
    try:
        while True:
            if app.state.current_autognome and app.state.current_autognome.running:
                auto = app.state.current_autognome
                
                try:
                    # Get action result
                    message = await auto.act()
                    
                    # Get status and check for observations
                    if app.state.websocket:
                        status = auto.get_status()
                        
                        # Send status update
                        await app.state.websocket.send_json({
                            "type": "status",
                            "data": status
                        })
                        
                        # Send observation message if any
                        if status.get("observation"):
                            await app.state.websocket.send_json({
                                "type": "message",
                                "data": status["observation"]
                            })
                        
                        # Send action message if any
                        if message:
                            await app.state.websocket.send_json({
                                "type": "message",
                                "data": message
                            })
                except Exception as e:
                    logger.exception("Error in pulse loop iteration")
                    if app.state.websocket:
                        try:
                            await app.state.websocket.send_json({
                                "type": "message",
                                "data": f"Error: {str(e)}"
                            })
                        except:
                            pass
                            
            # Use configured pulse frequency from core config
            await asyncio.sleep(auto.config.core["pulse_frequency"] if auto else 1.0)
    except asyncio.CancelledError:
        # Clean shutdown
        raise
    except Exception as e:
        logger.exception("Fatal error in pulse loop")
        if app.state.websocket:
            try:
                await app.state.websocket.send_json({
                    "type": "message",
                    "data": f"Fatal error: {str(e)}"
                })
            except:
                pass

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
                auto = app.state.current_autognome
                if not auto:
                    continue
                    
                # Handle commands
                if data.startswith("/"):
                    cmd = data.lstrip("/")
                    if cmd == "toggle_light":
                        current = auto._sensor.read_light_level()
                        new_level = "dark" if current == "light" else "light"
                        auto._sensor.set_light_level(new_level)
                        await websocket.send_json({
                            "type": "message",
                            "data": f"Light level changed to {new_level}."
                        })
                    elif cmd == "hello":
                        # Let the mind handle the greeting
                        context = auto._build_context()
                        actions = await auto._mind.think(context)
                        
                        # Execute first speak action if any
                        for action in actions:
                            if isinstance(action, Speak):
                                result = await action.execute(context)
                                if result.success:
                                    await websocket.send_json({
                                        "type": "message",
                                        "data": result.message
                                    })
                                    break
                        else:  # No speak action found
                            await websocket.send_json({
                                "type": "message",
                                "data": f"Hello! I am {auto.config.name}!"
                            })
                    elif cmd == "rest":
                        if auto.running:
                            # Let the mind handle resting
                            context = auto._build_context()
                            actions = [Rest(pulses=3)]  # Force a rest action
                            for action in actions:
                                result = await action.execute(context)
                                if result.success:
                                    await websocket.send_json({
                                        "type": "message",
                                        "data": "Taking a moment to rest..."
                                    })
                                    break
                        else:
                            await websocket.send_json({
                                "type": "message",
                                "data": "I'm sleeping right now. Use '/wake' to wake me up first."
                            })
                    elif cmd == "sleep":
                        if auto.running:
                            auto.stop()
                            await websocket.send_json({
                                "type": "message",
                                "data": "Going to sleep... Goodnight!"
                            })
                        else:
                            await websocket.send_json({
                                "type": "message",
                                "data": "I'm already sleeping."
                            })
                    elif cmd == "wake":
                        if not auto.running:
                            auto.running = True
                            await websocket.send_json({
                                "type": "message",
                                "data": "Good morning! I'm awake now."
                            })
                        else:
                            await websocket.send_json({
                                "type": "message",
                                "data": "I'm already awake!"
                            })
                    elif cmd == "help":
                        help_text = """Available commands:

/hello - Get a greeting from me
/status - Get my current status
/rest - Tell me to take a rest
/toggle_light - Toggle the light level
/sleep - Tell me to go to sleep
/wake - Wake me up from sleep
/help - Show this help message"""
                        await websocket.send_json({
                            "type": "message",
                            "data": help_text
                        })
                    elif cmd == "status":
                        # Send immediate status update
                        await websocket.send_json({
                            "type": "status",
                            "data": auto.get_status()
                        })
                    else:
                        await websocket.send_json({
                            "type": "message",
                            "data": f"'{cmd}' is not a recognized command. Type '/help' to see the list of available commands."
                        })
                else:
                    # Record user message for mind context
                    auto.record_user_message(data)
                    
            except asyncio.TimeoutError:
                pass  # No message received
            except Exception as e:
                if not isinstance(e, (asyncio.CancelledError, RuntimeError)):
                    print(f"Error handling message: {e}")
                break
                
    except Exception as e:
        if not isinstance(e, (asyncio.CancelledError, RuntimeError)):
            print(f"WebSocket connection error: {e}")
    finally:
        app.state.websocket = None
        try:
            await websocket.close()
        except:
            pass 