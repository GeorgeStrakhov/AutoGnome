from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich import box
from typing import List, Optional
from .ascii_art import get_gnome_art

console = Console()

class Message:
    def __init__(self, text: str, type: str = "thought"):
        self.text = text
        self.type = type
        self.timestamp = datetime.now().strftime('%H:%M:%S')

class ConsoleDisplay:
    def __init__(self, max_messages: int = 5):
        self.max_messages = max_messages
        self.messages: List[Message] = []
        self.layout = Layout()
        self.live = Live(self.layout, refresh_per_second=4, screen=True)

    def add_message(self, text: str, type: str = "thought") -> None:
        """Add a new message to the display"""
        self.messages.append(Message(text, type))
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def _create_status_table(self, status: dict) -> Table:
        """Create the status table"""
        table = Table(box=box.ROUNDED, expand=True, show_header=False)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in status.items():
            if key == "state":
                color = "green" if value == "active" else "yellow"
                table.add_row(key.title(), f"[{color}]{value}[/]")
            elif key == "energy":
                color = "red" if value < 5 else "yellow" if value < 7 else "green"
                table.add_row(key.title(), f"[{color}]{value:.1f}[/]")
            else:
                table.add_row(key.title(), str(value))
        
        return table

    def _create_message_panel(self) -> Panel:
        """Create the message history panel"""
        message_text = "\n".join(
            f"[{msg.timestamp}] {msg.text}"
            for msg in self.messages
        )
        return Panel(
            message_text,
            title="💭 Thoughts",
            border_style="bright_magenta"
        )

    def update(self, status: dict) -> None:
        """Update the display with new status"""
        # Create main layout
        self.layout.split_column(
            Layout(name="top"),
            Layout(name="bottom", size=10)
        )
        
        # Create top layout with status and art
        self.layout["top"].split_row(
            Layout(
                Panel(
                    self._create_status_table(status),
                    title="🤖 Status",
                    border_style="bright_blue"
                ),
                ratio=2
            ),
            Layout(
                Panel(
                    get_gnome_art(status.get("state", "normal")),
                    title=f"🧙 AutoGnome: AG-{status.get('identifier', '')}, {status.get('name', '')}",
                    border_style="bright_green"
                ),
                ratio=1
            )
        )
        
        # Add message panel at the bottom
        self.layout["bottom"].update(self._create_message_panel())

    def start(self) -> None:
        """Start the live display"""
        self.live.start()

    def stop(self) -> None:
        """Stop the live display"""
        self.live.stop()

    def print_startup(self, name: str, identifier: str, frequency: float) -> None:
        """Print the startup message"""
        console.print(Panel(
            f"[bold]Name:[/] {name}\n[bold]Pulse Frequency:[/] {frequency}s",
            title=f"🚀 AutoGnome: AG-{identifier}",
            border_style="green"
        ))
        console.print("─" * console.width, style="bright_black") 