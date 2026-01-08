"""
GlassTrax API Agent - Command Line Interface

Entry point with support for different run modes:
- --tray: System tray application (default for EXE)
- --service: Windows service mode (for NSSM)
- --console: Console mode with logging (for debugging)
"""

import argparse
import multiprocessing
import sys

import uvicorn

from agent import __version__
from agent.config import get_config


def run_server(host: str = "0.0.0.0", port: int | None = None) -> None:
    """Run the uvicorn server"""
    config = get_config()
    uvicorn.run(
        "agent.main:app",
        host=host,
        port=port or config.port,
        reload=False,
        log_level="info",
    )


def run_tray_mode(auto_start: bool = True) -> None:
    """Run with system tray icon"""
    try:
        from agent.tray_app import AgentTray
    except ImportError as e:
        print(f"Error: System tray dependencies not installed: {e}")
        print("Install with: pip install pystray Pillow")
        sys.exit(1)

    tray = AgentTray()
    tray.run(auto_start=auto_start)


def run_console_mode(host: str, port: int | None) -> None:
    """Run in console mode with visible output"""
    config = get_config()
    actual_port = port or config.port

    print()
    print("=" * 50)
    print(f"  GlassTrax API Agent v{__version__}")
    print("=" * 50)
    print()
    print(f"  Host: {host}")
    print(f"  Port: {actual_port}")
    print(f"  DSN:  {config.dsn}")
    print()
    print("  Press Ctrl+C to stop")
    print()
    print("=" * 50)
    print()

    run_server(host, port)


def run_service_mode(host: str, port: int | None) -> None:
    """Run as background service (no console output)"""
    run_server(host, port)


def main() -> int:
    """Main entry point"""
    # Required for embedded Python / PyInstaller
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(
        description="GlassTrax API Agent - ODBC Query Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agent.cli --tray              Run with system tray (default for installer)
  agent.cli --console           Run in console with logging
  agent.cli --service           Run as background service (NSSM)
  agent.cli --console --port 8002  Run on different port
""",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"GlassTrax API Agent {__version__}",
    )

    # Run modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--tray",
        action="store_true",
        help="Run with system tray icon (default for EXE)",
    )
    mode_group.add_argument(
        "--service",
        action="store_true",
        help="Run as background service (for NSSM)",
    )
    mode_group.add_argument(
        "--console",
        action="store_true",
        help="Run in console mode with logging",
    )

    # Configuration overrides
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port to listen on (default: from config)",
    )
    parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help="Don't auto-start agent in tray mode",
    )

    args = parser.parse_args()

    # Determine mode
    if args.tray:
        run_tray_mode(auto_start=not args.no_auto_start)
    elif args.service:
        run_service_mode(args.host, args.port)
    elif args.console:
        run_console_mode(args.host, args.port)
    else:
        # Default: tray mode if running as EXE (no console), else console
        # Check if running via pythonw.exe or frozen (bundled EXE)
        is_gui_mode = (
            sys.executable.lower().endswith("pythonw.exe")
            or getattr(sys, "frozen", False)
            or not sys.stdout.isatty()
        )

        if is_gui_mode:
            run_tray_mode()
        else:
            run_console_mode(args.host, args.port)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("\n" + "=" * 50)
        print("ERROR: Agent failed to start")
        print("=" * 50)
        print(f"\n{type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 50)
        input("Press Enter to exit...")
        sys.exit(1)
