"""
GlassTrax Agent - System Tray Application

Provides a system tray icon with start/stop controls and status monitoring.
Uses pystray for cross-platform system tray support.
"""

import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from PIL import Image
from pystray import Icon, Menu, MenuItem

from agent import __version__
from agent.config import get_config, get_config_dir


def setup_logging() -> Path:
    """
    Configure logging to a file that recreates on each run.
    Returns the log file path.
    """
    log_dir = get_config_dir()
    log_file = log_dir / "agent.log"

    # Clear log file on each run
    log_file.write_text("")

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
    )

    # Reduce noise from uvicorn access logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return log_file


class AgentTray:
    """System tray application for GlassTrax Agent"""

    # Icon states
    STATE_STOPPED = "stopped"
    STATE_RUNNING = "running"
    STATE_ERROR = "error"

    def __init__(self):
        self._state = self.STATE_STOPPED
        self._icon: Optional[Icon] = None
        self._server: Optional[uvicorn.Server] = None
        self._server_thread: Optional[threading.Thread] = None
        self._config = get_config()
        self._log_file = setup_logging()
        self._logger = logging.getLogger("agent.tray")

        # Load icons
        self._icons = self._load_icons()

        self._logger.info(f"GlassTrax Agent v{__version__} initialized")

    def _load_icons(self) -> dict:
        """Load tray icons from icons/ directory or generate defaults"""
        icons_dir = Path(__file__).parent / "icons"
        icons = {}

        # Try to load from files
        icon_files = {
            self.STATE_RUNNING: "icon_running.ico",
            self.STATE_STOPPED: "icon_stopped.ico",
            self.STATE_ERROR: "icon_error.ico",
        }

        for state, filename in icon_files.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                try:
                    icons[state] = Image.open(icon_path)
                    continue
                except Exception:
                    pass

            # Generate simple colored icon as fallback
            icons[state] = self._generate_icon(state)

        return icons

    def _generate_icon(self, state: str) -> Image.Image:
        """Generate a simple colored icon"""
        colors = {
            self.STATE_RUNNING: (34, 197, 94),  # Green #22c55e
            self.STATE_STOPPED: (239, 68, 68),  # Red #ef4444
            self.STATE_ERROR: (234, 179, 8),  # Yellow #eab308
        }
        color = colors.get(state, (128, 128, 128))

        # Create a 64x64 icon with the colored circle
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

        # Draw a filled circle
        from PIL import ImageDraw

        draw = ImageDraw.Draw(img)
        margin = 4
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=color + (255,),
            outline=(255, 255, 255, 255),
            width=2,
        )

        return img

    def _create_menu(self) -> Menu:
        """Create the context menu with dynamic items"""
        # Use lambdas for dynamic text/enabled state (pystray requirement)
        return Menu(
            MenuItem(
                lambda item: "Stop Agent" if self._state == self.STATE_RUNNING else "Start Agent",
                self._toggle_agent,
            ),
            Menu.SEPARATOR,
            MenuItem(
                "Open Health Check",
                self._open_health,
                enabled=lambda item: self._state == self.STATE_RUNNING,
            ),
            MenuItem(
                "Open API Docs",
                self._open_docs,
                enabled=lambda item: self._state == self.STATE_RUNNING,
            ),
            Menu.SEPARATOR,
            MenuItem(
                f"Version: {__version__}",
                None,
                enabled=False,
            ),
            MenuItem(
                f"Port: {self._config.port}",
                None,
                enabled=False,
            ),
            MenuItem(
                f"DSN: {self._config.dsn}",
                None,
                enabled=False,
            ),
            Menu.SEPARATOR,
            MenuItem("Open Config Folder", self._open_config_folder),
            MenuItem("View Log File", self._open_log),
            MenuItem("Exit", self._exit),
        )

    def _toggle_agent(self, icon, item) -> None:
        """Start or stop the agent"""
        if self._state == self.STATE_STOPPED:
            self._start_agent()
        else:
            self._stop_agent()

    def _start_agent(self) -> None:
        """Start the agent server in a background thread"""
        if self._state == self.STATE_RUNNING:
            return

        try:
            self._logger.info(f"Starting agent on port {self._config.port}")

            # Configure uvicorn with logging disabled (we handle logging ourselves)
            config = uvicorn.Config(
                "agent.main:app",
                host="0.0.0.0",
                port=self._config.port,
                log_level="warning",
                log_config=None,  # Disable uvicorn's log config to avoid formatter errors
            )
            self._server = uvicorn.Server(config)

            # Start in background thread
            self._server_thread = threading.Thread(
                target=self._server.run,
                daemon=True,
            )
            self._server_thread.start()

            self._set_state(self.STATE_RUNNING)
            self._logger.info(f"Agent started successfully on port {self._config.port}")
            self._notify("GlassTrax Agent Started", f"Listening on port {self._config.port}")

        except Exception as e:
            self._logger.exception("Failed to start agent")
            self._set_state(self.STATE_ERROR)
            self._notify("Failed to Start Agent", str(e))

    def _stop_agent(self) -> None:
        """Stop the agent server"""
        if self._state == self.STATE_STOPPED:
            return

        try:
            self._logger.info("Stopping agent...")

            if self._server:
                self._server.should_exit = True

            # Wait for thread to finish (with timeout)
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5.0)

            self._server = None
            self._server_thread = None
            self._set_state(self.STATE_STOPPED)
            self._logger.info("Agent stopped")
            self._notify("GlassTrax Agent Stopped", "Agent has been stopped")

        except Exception as e:
            self._logger.exception("Error stopping agent")
            self._set_state(self.STATE_ERROR)
            self._notify("Error Stopping Agent", str(e))

    def _set_state(self, state: str) -> None:
        """Update icon state and refresh menu"""
        self._state = state
        if self._icon:
            self._icon.icon = self._icons[state]
            self._icon.update_menu()

    def _notify(self, title: str, message: str) -> None:
        """Show a notification"""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass  # Notifications may not be supported on all systems

    def _open_health(self, icon, item) -> None:
        """Open health check in browser"""
        webbrowser.open(f"http://localhost:{self._config.port}/health")

    def _open_docs(self, icon, item) -> None:
        """Open API docs in browser"""
        webbrowser.open(f"http://localhost:{self._config.port}/docs")

    def _open_config_folder(self, icon, item) -> None:
        """Open the config folder in explorer"""
        config_path = get_config_dir()
        if sys.platform == "win32":
            os.startfile(str(config_path))
        else:
            webbrowser.open(f"file://{config_path}")

    def _open_log(self, icon, item) -> None:
        """Open the log file in default text editor"""
        if self._log_file.exists():
            if sys.platform == "win32":
                os.startfile(str(self._log_file))
            else:
                webbrowser.open(f"file://{self._log_file}")

    def _exit(self, icon, item) -> None:
        """Exit the application"""
        if self._state == self.STATE_RUNNING:
            self._stop_agent()
        if icon:
            icon.stop()

    def run(self, auto_start: bool = True) -> None:
        """Run the tray application"""
        self._icon = Icon(
            "GlassTrax Agent",
            self._icons[self.STATE_STOPPED],
            "GlassTrax Agent",
            menu=self._create_menu(),
        )

        if auto_start:
            # Schedule auto-start after icon is ready
            def on_ready(icon):
                # Set to running icon BEFORE showing (so notification uses green icon)
                icon.icon = self._icons[self.STATE_RUNNING]
                icon.visible = True
                self._start_agent()

            self._icon.run(setup=on_ready)
        else:
            self._icon.run()
