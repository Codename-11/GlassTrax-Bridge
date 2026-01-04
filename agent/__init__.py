"""
GlassTrax Agent

Minimal ODBC query service for GlassTrax ERP.
Runs on Windows with 32-bit Python for Pervasive ODBC driver compatibility.
"""

from pathlib import Path


def _get_version() -> str:
    """Read version from VERSION file"""
    # Look for VERSION in project root (parent of agent/)
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Fallback for bundled EXE (VERSION copied to app directory)
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    return "0.0.0"


__version__ = _get_version()
