from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict
import asyncio
import json
import os

from ..core.autognome import Autognome
from ..core.config import AutognomeConfig
from ..display.ascii_art import get_gnome_art

app = FastAPI()

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

    async def broadcast_status(self, status: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "status",
                    "data": status
                })
            except:
                pass

manager = ConnectionManager()
autognome: Autognome = None

def get_current_autognome() -> Autognome:
    """Get the current autognome instance"""
    return autognome

async def run_autognome():
    """Run the autognome in the background"""
    global autognome
    
    if not autognome:
        autognome = Autognome(
            identifier="8",
            name="Echo",
            config=AutognomeConfig(
                initial_energy=10.0,
                optimal_energy=7.0,
                energy_depletion_rate=1.0,
                energy_recovery_rate=1.0,
                dark_fear_threshold=0.7,
                light_confidence_boost=0.3
            )
        )
    
    while True:
        if autognome.running:
            message = autognome.act()
            if message != "...":
                await manager.broadcast(message)
            
            # Send status update
            status = autognome.get_status()
            status["ascii_art"] = get_gnome_art(
                state=status.get("display_state", "normal"),
                is_observing=status.get("is_observing", False)
            )
            await manager.broadcast_status(status)
            
        await asyncio.sleep(autognome.config.pulse_frequency)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_autognome())

@app.on_event("shutdown")
async def shutdown_event():
    """Handle graceful shutdown"""
    global autognome
    if autognome and autognome.running:
        autognome.stop()
        # Save final state
        autognome._save_state()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main page"""
    with open(os.path.join(static_dir, "index.html")) as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            command = data.lower().strip()
            
            if command == "status":
                status = autognome.get_status()
                status["ascii_art"] = get_gnome_art(
                    state=status.get("display_state", "normal"),
                    is_observing=status.get("is_observing", False)
                )
                await websocket.send_json({
                    "type": "status",
                    "data": status
                })
            elif command == "hello":
                await websocket.send_text(f"Hello! I am {autognome.name}, AG-{autognome.identifier}.")
            elif command == "help":
                help_text = """Available commands:
• hello - Get a greeting from the autognome
• status - Get current status
• rest - Take a rest to recover energy
• stats - Get detailed statistics
• help - Show this help message"""
                await websocket.send_text(help_text)
            elif command == "rest":
                if not autognome.is_resting:
                    autognome.start_rest()
                    await websocket.send_text("Taking a moment to rest...")
                else:
                    await websocket.send_text("Already resting...")
            elif command == "stats":
                lifetime = autognome.get_lifetime_stats()
                stats_text = f"""Lifetime Statistics:
• Wake cycles: {lifetime['wake_count']}
• Total runtime: {lifetime['total_runtime']:.1f}s
• Total hibernation: {lifetime['total_hibernation_time']:.1f}s
• Total pulses: {lifetime['total_pulses']}
• Total rests: {lifetime['total_rests']}"""
                await websocket.send_text(stats_text)
            elif command == "toggle_light":
                # Toggle the light level
                current = autognome._sensor.read_light_level()
                new_level = "dark" if current == "light" else "light"
                autognome._sensor.set_light_level(new_level)
                
                # Send immediate status update
                status = autognome.get_status()
                status["ascii_art"] = get_gnome_art(
                    state=status.get("display_state", "normal"),
                    is_observing=status.get("is_observing", False)
                )
                await websocket.send_json({
                    "type": "status",
                    "data": status
                })
            else:
                await websocket.send_text(f"Unknown command. Type 'help' for available commands.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket) 