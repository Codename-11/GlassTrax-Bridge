"""
Agent Configuration

Loads and manages agent_config.yaml settings.
"""

import os
import secrets
import sys
from pathlib import Path
from typing import Any

import bcrypt
from ruamel.yaml import YAML


def get_install_dir() -> Path:
    """Get the installation directory (where agent/ folder is)"""
    return Path(__file__).parent.parent


def get_config_dir() -> Path:
    """
    Get the config directory.

    Uses %APPDATA%/GlassTrax API Agent on Windows for user-writable storage.
    Falls back to install directory for development/portable mode.
    """
    # Check if running from Program Files (installed mode)
    install_dir = get_install_dir()
    is_installed = "Program Files" in str(install_dir)

    if is_installed and sys.platform == "win32":
        # Use AppData for installed mode (user-writable)
        appdata = os.environ.get("APPDATA")
        if appdata:
            config_dir = Path(appdata) / "GlassTrax API Agent"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir

    # Development/portable mode - use install directory
    return install_dir


def get_config_path() -> Path:
    """Get path to agent_config.yaml"""
    return get_config_dir() / "agent_config.yaml"


class AgentConfig:
    """Agent configuration manager"""

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._new_api_key: str | None = None  # Set if key was just generated
        self.load()

    def load(self) -> None:
        """Load configuration from agent_config.yaml"""
        config_path = get_config_path()

        if not config_path.exists():
            self._create_default_config(config_path)

        with open(config_path, encoding="utf-8") as f:
            self._config = self._yaml.load(f) or {}

        # Generate API key on first run if not set
        if not self._config.get("agent", {}).get("api_key_hash"):
            self._generate_api_key(config_path)

    def _create_default_config(self, path: Path) -> None:
        """Create default configuration file"""
        default_config = {
            "database": {
                "dsn": "LIVE",
                "readonly": True,
                "timeout": 30,
                "query_timeout": 60,  # Max seconds per query execution
            },
            "agent": {
                "port": 8001,
                "api_key_hash": "",
                "test_query": "SELECT 1",  # Query to run for health checks
                "allowed_tables": [
                    "customer",
                    "customer_contacts",
                    "delivery_routes",
                    "sales_orders_headers",
                    "sales_order_detail",
                    "so_processing",
                    "processing_charges",
                ],
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            self._yaml.dump(default_config, f)

        self._config = default_config

    def _generate_api_key(self, config_path: Path) -> None:
        """Generate a new API key and save the hash"""
        # Generate a secure random key with prefix
        raw_key = secrets.token_urlsafe(32)
        api_key = f"gta_{raw_key}"  # gta = glasstrax agent

        # Hash the key for storage
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

        # Update config
        if "agent" not in self._config:
            self._config["agent"] = {}
        self._config["agent"]["api_key_hash"] = key_hash

        # Save to file
        with open(config_path, "w", encoding="utf-8") as f:
            self._yaml.dump(self._config, f)

        # Store for tray app to retrieve and log/notify
        self._new_api_key = api_key

        # Also print to console (for console mode)
        print("\n" + "=" * 60)
        print("GLASSTRAX AGENT - FIRST RUN")
        print("=" * 60)
        print("\nA new API key has been generated. SAVE THIS KEY!")
        print(f"\n  Agent API Key: {api_key}")
        print("\nConfigure this key in your main API's config.yaml:")
        print("  agent:")
        print("    enabled: true")
        print(f'    api_key: "{api_key}"')
        print("=" * 60 + "\n")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., 'database.dsn')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split(".")
        value = self._config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def verify_api_key(self, key: str) -> bool:
        """
        Verify an API key against the stored hash.

        Args:
            key: API key to verify

        Returns:
            True if key is valid
        """
        stored_hash = self.get("agent.api_key_hash", "")
        if not stored_hash:
            return False

        try:
            return bcrypt.checkpw(key.encode(), stored_hash.encode())
        except Exception:
            return False

    def regenerate_api_key(self) -> str:
        """
        Generate a new API key, save the hash, and return the plain key.

        Returns:
            The new API key (plain text) - only chance to see it!
        """
        config_path = get_config_path()

        # Generate a secure random key with prefix
        raw_key = secrets.token_urlsafe(32)
        api_key = f"gta_{raw_key}"

        # Hash the key for storage
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

        # Update config
        if "agent" not in self._config:
            self._config["agent"] = {}
        self._config["agent"]["api_key_hash"] = key_hash

        # Save to file
        with open(config_path, "w", encoding="utf-8") as f:
            self._yaml.dump(self._config, f)

        return api_key

    def get_new_api_key(self) -> str | None:
        """
        Get newly generated API key (first run only).
        Returns the key and clears it so it's only returned once.
        """
        key = self._new_api_key
        self._new_api_key = None
        return key

    @property
    def dsn(self) -> str:
        """Get configured DSN"""
        return self.get("database.dsn", "LIVE")

    @property
    def readonly(self) -> bool:
        """Get readonly setting"""
        return self.get("database.readonly", True)

    @property
    def timeout(self) -> int:
        """Get connection timeout"""
        return self.get("database.timeout", 30)

    @property
    def query_timeout(self) -> int:
        """Get query execution timeout (max seconds per query)"""
        return self.get("database.query_timeout", 60)

    @property
    def port(self) -> int:
        """Get agent port"""
        return self.get("agent.port", 8001)

    @property
    def allowed_tables(self) -> list[str]:
        """Get list of allowed table names"""
        return self.get("agent.allowed_tables", [])

    @property
    def test_query(self) -> str:
        """Get health check test query"""
        return self.get("agent.test_query", "SELECT 1")


# Global config instance
_config: AgentConfig | None = None


def get_config() -> AgentConfig:
    """Get the global config instance"""
    global _config
    if _config is None:
        _config = AgentConfig()
    return _config
