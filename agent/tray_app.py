"""
GlassTrax API Agent - System Tray Application

Provides a system tray icon with start/stop controls and status monitoring.
Uses pystray for cross-platform system tray support.
"""

import logging
import os
import sys
import threading
import webbrowser
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import uvicorn
from PIL import Image
from pystray import Icon, Menu, MenuItem

from agent import __version__
from agent.config import get_config, get_config_dir

# Import updater with fallback if it fails
try:
    from agent.updater import ReleaseInfo, UpdateChecker
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    UpdateChecker = None
    ReleaseInfo = None
    # Will log this later when logger is available


def setup_logging() -> Path:
    """
    Configure logging with daily rotation and configurable retention.
    Returns the log file path.
    """
    log_dir = get_config_dir()
    log_file = log_dir / "agent.log"

    # Get retention days from config (default 7)
    config = get_config()
    retention_days = config.log_retention_days

    # Create rotating file handler - rotates at midnight daily
    # backupCount = retention_days means keep that many old log files
    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"  # Rotated files: agent.log.2026-01-18

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%m/%d/%y - %I:%M %p",
        handlers=[handler],
    )

    # Reduce noise from uvicorn access logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return log_file


class AgentTray:
    """System tray application for GlassTrax API Agent"""

    # Icon states
    STATE_STOPPED = "stopped"
    STATE_RUNNING = "running"
    STATE_ERROR = "error"

    def __init__(self):
        self._state = self.STATE_STOPPED
        self._icon: Icon | None = None
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._config = get_config()
        self._log_file = setup_logging()
        self._logger = logging.getLogger("agent.tray")

        # Log session start separator
        self._logger.info("=" * 50)
        self._logger.info(f"GlassTrax API Agent v{__version__} starting")
        self._logger.info("=" * 50)

        # Check for first-run API key generation
        new_key = self._config.get_new_api_key()
        if new_key:
            self._logger.info("-" * 40)
            self._logger.info("FIRST RUN - API KEY GENERATED")
            self._logger.info(f"API Key: {new_key}")
            self._logger.info("Save this key! View Log File to see it again.")
            self._logger.info("-" * 40)
            # Store for notification after icon is ready
            self._first_run_key = new_key
        else:
            self._first_run_key = None

        # Load icons
        self._icons = self._load_icons()

        # Initialize updater (if available)
        self._update_available = False
        if UPDATER_AVAILABLE:
            self._updater = UpdateChecker(
                on_update_available=self._on_update_available,
                on_check_complete=self._on_update_check_complete,
                on_download_complete=self._on_download_complete,
                on_download_failed=self._on_download_failed,
            )
        else:
            self._updater = None
            self._logger.warning("Updater not available - update features disabled")

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
        menu_items = [
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
        ]

        # Add update menu items if updater is available
        if UPDATER_AVAILABLE and self._updater:
            menu_items.extend([
                Menu.SEPARATOR,
                MenuItem(
                    lambda item: "Update Available!" if self._update_available else "Check for Updates",
                    self._check_for_updates,
                ),
                MenuItem(
                    "Download Update",
                    self._download_update,
                    visible=lambda item: self._update_available,
                ),
                MenuItem(
                    "View Release Notes",
                    self._view_release_notes,
                ),
            ])

        menu_items.extend([
            Menu.SEPARATOR,
            MenuItem("Regenerate API Key", self._regenerate_api_key),
            MenuItem("Open Config Folder", self._open_config_folder),
            MenuItem("View Log File", self._open_log),
            MenuItem("Exit", self._exit),
        ])

        return Menu(*menu_items)

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

            # Check if port is already in use
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(("0.0.0.0", self._config.port))
                sock.close()
            except OSError as e:
                self._logger.error(f"Port {self._config.port} is already in use: {e}")
                self._set_state(self.STATE_ERROR)
                self._notify("Failed to Start Agent", f"Port {self._config.port} is already in use")
                return

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

            # Wait briefly for server to start and verify it's listening
            import time
            time.sleep(0.5)
            if not self._server.started:
                time.sleep(1.0)  # Give it a bit more time

            if self._server.started:
                self._set_state(self.STATE_RUNNING)
                self._logger.info(f"Agent started successfully on port {self._config.port}")
                self._notify("GlassTrax API Agent Started", f"Listening on port {self._config.port}")
            else:
                self._logger.error("Agent failed to start - server not listening")
                self._set_state(self.STATE_ERROR)
                self._notify("Failed to Start Agent", "Server failed to bind")

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
            self._notify("GlassTrax API Agent Stopped", "Agent has been stopped")

        except Exception as e:
            self._logger.exception("Error stopping agent")
            self._set_state(self.STATE_ERROR)
            self._notify("Error Stopping Agent", str(e))

    def _set_state(self, state: str) -> None:
        """Update icon state and refresh menu"""
        old_state = self._state
        self._state = state
        if old_state != state:
            self._logger.info(f"Agent state: {old_state} -> {state}")
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

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard (Windows only)"""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            CF_UNICODETEXT = 13
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32

            user32.OpenClipboard(0)
            user32.EmptyClipboard()

            # Allocate global memory
            hMem = kernel32.GlobalAlloc(0x0042, (len(text) + 1) * 2)
            pMem = kernel32.GlobalLock(hMem)
            ctypes.cdll.msvcrt.wcscpy(ctypes.c_wchar_p(pMem), text)
            kernel32.GlobalUnlock(hMem)

            user32.SetClipboardData(CF_UNICODETEXT, hMem)
            user32.CloseClipboard()
            return True
        except Exception:
            return False

    def _show_message_box(self, title: str, message: str, style: int = 0) -> int:
        """Show a Windows message box. Returns button clicked (1=OK, 6=Yes, 7=No, 2=Cancel)"""
        if sys.platform != "win32":
            return 1  # Default to OK on non-Windows
        try:
            import ctypes
            return ctypes.windll.user32.MessageBoxW(0, message, title, style)
        except Exception:
            return 1

    def _regenerate_api_key(self, icon, item) -> None:
        """Regenerate the API key with confirmation and visual display"""
        # Show warning dialog (MB_YESNO | MB_ICONWARNING = 0x04 | 0x30 = 0x34)
        result = self._show_message_box(
            "Regenerate API Key",
            "Are you sure you want to regenerate the API key?\n\n"
            "WARNING: The current key will be invalidated immediately.\n"
            "Any systems using the old key will lose access.\n\n"
            "Click Yes to generate a new key.\n"
            "Click No to cancel.",
            0x34  # MB_YESNO | MB_ICONWARNING
        )

        if result != 6:  # 6 = IDYES
            self._logger.info("API key regeneration cancelled by user")
            return

        try:
            new_key = self._config.regenerate_api_key()
            self._logger.info("-" * 40)
            self._logger.info("API KEY REGENERATED")
            self._logger.info(f"New Key: {new_key}")
            self._logger.info("-" * 40)

            # Copy to clipboard
            copied = self._copy_to_clipboard(new_key)

            # Show the new key in a dialog (MB_OK | MB_ICONINFORMATION = 0x00 | 0x40 = 0x40)
            clipboard_msg = "\n\nKey copied to clipboard!" if copied else ""
            self._show_message_box(
                "New API Key Generated",
                f"Your new API key:\n\n{new_key}\n\n"
                f"Save this key securely - it won't be shown again.{clipboard_msg}\n\n"
                f"The key is also saved to the log file.",
                0x40  # MB_OK | MB_ICONINFORMATION
            )

            self._notify("API Key Regenerated", "New key generated and copied to clipboard")

        except Exception as e:
            self._logger.exception("Failed to regenerate API key")
            self._show_message_box(
                "Error",
                f"Failed to regenerate API key:\n\n{e}",
                0x10  # MB_OK | MB_ICONERROR
            )

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

    # --- Update Methods ---

    def _check_for_updates(self, icon, item) -> None:
        """Check for updates manually"""
        self._logger.info("Manual update check requested")
        self._updater.check_async()

    def _download_update(self, icon, item) -> None:
        """Download the available update"""
        if self._update_available and self._updater.latest_release:
            self._notify("Downloading Update",
                        f"Downloading v{self._updater.latest_release.version}...")
            self._updater.download_update()

    def _view_release_notes(self, icon, item) -> None:
        """Open GitHub releases page in browser"""
        webbrowser.open(self._updater.get_releases_url())

    def _on_update_available(self, release: ReleaseInfo) -> None:
        """Callback when an update is available"""
        self._update_available = True
        if self._icon:
            self._icon.update_menu()
        self._notify(
            "Update Available",
            f"Version {release.version} is available (current: {__version__})"
        )

    def _on_update_check_complete(self, has_update: bool) -> None:
        """Callback when update check completes"""
        if self._icon:
            self._icon.update_menu()
        # Show notification when up to date
        if not has_update:
            self._notify("Up to Date", f"You have the latest version (v{__version__})")

    def _on_download_complete(self, installer_path) -> None:
        """Callback when download completes"""
        self._notify("Download Complete", "Click 'Download Update' to install, or run installer manually.")
        self._logger.info(f"Update downloaded to: {installer_path}")

        # Optionally auto-launch installer
        if self._updater.install_update(installer_path):
            self._logger.info("Installer launched, exiting agent...")
            # Give installer time to start before we exit
            import time
            time.sleep(1)
            self._exit(self._icon, None)

    def _on_download_failed(self, error: str) -> None:
        """Callback when download fails"""
        self._notify("Download Failed", f"Error: {error}")
        self._logger.error(f"Update download failed: {error}")

    def _exit(self, icon, item) -> None:
        """Exit the application"""
        self._logger.info("Exit requested, shutting down...")
        if self._state == self.STATE_RUNNING:
            self._stop_agent()
        if icon:
            icon.stop()
        # Force exit to ensure all threads are terminated
        import os
        os._exit(0)

    def run(self, auto_start: bool = True) -> None:
        """Run the tray application"""
        self._logger.info("Creating system tray icon...")

        try:
            menu = self._create_menu()
            self._logger.info("Menu created successfully")
        except Exception as e:
            self._logger.exception(f"Failed to create menu: {e}")
            raise

        try:
            self._icon = Icon(
                "GlassTrax API Agent",
                self._icons[self.STATE_STOPPED],
                "GlassTrax API Agent",
                menu=menu,
            )
            self._logger.info("Icon object created")
        except Exception as e:
            self._logger.exception(f"Failed to create icon: {e}")
            raise

        if auto_start:
            # Schedule auto-start after icon is ready
            def on_ready(icon):
                try:
                    self._logger.info("Tray icon ready, initializing...")

                    # Set to running icon BEFORE showing (so notification uses green icon)
                    icon.icon = self._icons[self.STATE_RUNNING]
                    icon.visible = True
                    self._start_agent()

                    # Show first-run API key notification
                    if self._first_run_key:
                        if self._copy_to_clipboard(self._first_run_key):
                            self._notify("First Run - API Key Generated",
                                       "Key copied to clipboard! Also saved to log file.")
                        else:
                            self._notify("First Run - API Key Generated",
                                       "Check log file for your API key.")
                        self._first_run_key = None

                    # Schedule update check after 15 seconds (if updater available)
                    if self._updater:
                        self._logger.info("Scheduling update check in 15 seconds")
                        self._updater.check_async(delay=15)

                except Exception as e:
                    self._logger.exception(f"Error in on_ready callback: {e}")

            self._logger.info("Starting icon.run() with auto_start...")
            self._icon.run(setup=on_ready)
            self._logger.info("icon.run() returned")
        else:
            self._logger.info("Starting icon.run() without auto_start...")
            self._icon.run()
            self._logger.info("icon.run() returned")
