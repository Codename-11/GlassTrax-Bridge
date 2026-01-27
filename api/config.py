### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Configuration -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Configuration Management

Uses Pydantic Settings for configuration with environment variable support.
Loads settings from .env file and data/config.yaml.

Config file location (in order of precedence):
1. GLASSTRAX_CONFIG_PATH environment variable
2. data/config.yaml (default - persisted in Docker via volume mount)
3. config.yaml in project root (legacy fallback for backwards compatibility)
"""

import os
from functools import lru_cache
from pathlib import Path

import bcrypt
import yaml
from pydantic_settings import BaseSettings


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


def get_config_path() -> Path:
    """
    Get the path to config.yaml.

    Priority:
    1. GLASSTRAX_CONFIG_PATH environment variable (if set)
    2. data/config.yaml (default location, persisted via Docker volume)
    3. config.yaml in project root (legacy fallback)
    """
    # Check environment variable first
    env_path = os.environ.get("GLASSTRAX_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    project_root = get_project_root()

    # Default location: data/config.yaml
    data_config = project_root / "data" / "config.yaml"

    # Legacy location: config.yaml in project root
    legacy_config = project_root / "config.yaml"

    # If data/config.yaml exists, use it
    if data_config.exists():
        return data_config

    # If legacy config exists but data/config.yaml doesn't, use legacy
    # (backwards compatibility for existing installations)
    if legacy_config.exists():
        return legacy_config

    # Default to data/config.yaml (will be created if missing)
    return data_config


def get_version() -> str:
    """Read version from VERSION file"""
    version_file = get_project_root() / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


class APISettings(BaseSettings):
    """API Server Settings"""

    # API Configuration
    api_title: str = "GlassTrax Bridge API"
    api_version: str = get_version()
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Database Configuration (for app DB - SQLite)
    app_database_url: str = "sqlite:///./data/glasstrax_bridge.db"

    # Security
    api_key_header: str = "X-API-Key"
    secret_key: str = "change-this-in-production"  # Used for JWT signing

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True

    # Timezone (loaded from config.yaml)
    timezone: str = "UTC"

    class Config:
        env_prefix = "GLASSTRAX_"
        env_file = ".env"
        extra = "ignore"


class GlassTraxDBSettings(BaseSettings):
    """GlassTrax Database Connection Settings"""

    friendly_name: str = "GlassTrax Database"
    dsn: str = "LIVE"  # ODBC Data Source Name
    readonly: bool = True
    timeout: int = 30

    class Config:
        env_prefix = "DB_"
        env_file = ".env"
        extra = "ignore"


DEFAULT_CONFIG = """# GlassTrax Bridge Configuration
# Main configuration file for database connections and application settings

# Database Configuration
database:
  # Friendly name shown in the UI (e.g., "TGI Database", "Production DB")
  friendly_name: "GlassTrax Database"

  # ODBC Data Source Name (DSN)
  # Configure this DSN in Windows ODBC Data Source Administrator (32-bit)
  # The DSN contains all connection details (server, driver, protocol, etc.)
  dsn: "LIVE"

  # Connection Options
  readonly: true              # Always connect in read-only mode for safety
  timeout: 30                 # Query timeout in seconds

# Application Settings
application:
  # Timezone for logs and timestamps (IANA timezone name)
  # Examples: America/New_York, America/Los_Angeles, Europe/London, UTC
  timezone: "America/New_York"

  # Logging Configuration
  # NOTE: Not yet implemented - currently hardcoded in middleware
  # See TODO.md for details
  logging:
    level: "INFO"             # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_to_file: true         # Enable file logging
    log_to_console: true      # Enable console logging

  # Performance Settings
  # NOTE: Not yet implemented - placeholders for future use
  # See TODO.md for details
  performance:
    query_timeout: 60        # Query timeout in seconds
    fetch_size: 1000         # Number of rows to fetch at once

# Feature Flags
features:
  enable_caching: true       # Enable FAB order query caching
  enable_exports: true       # NOT IMPLEMENTED - Data export functionality

# Caching Configuration
# Controls FAB order (/orders/fabs) response caching
caching:
  fabs_ttl_minutes: 30       # How long to cache FAB order responses (default: 30 min)
  max_cached_dates: 7        # Maximum number of dates to keep cached

# Admin Portal Authentication
# If not configured, defaults to admin/admin (change in production!)
admin:
  username: "admin"
  # password_hash: "$2b$12$..."  # Generate with: python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
  # Leave password_hash commented out to use default password 'admin'

# GlassTrax API Agent Settings
# Configure connection to Windows-based GlassTrax API Agent for database access
agent:
  # Enable agent mode (required when running in Docker)
  enabled: false
  # Agent URL (Windows machine running the agent)
  url: "http://localhost:8001"
  # Agent API key (generated when agent first starts)
  api_key: ""
  # Request timeout in seconds
  timeout: 30
"""


def load_yaml_config(config_path: str | None = None) -> dict:
    """Load configuration from YAML file, creating default if missing"""
    config_file = get_config_path() if config_path is None else Path(config_path)

    if not config_file.exists():
        # Ensure parent directory exists (for data/config.yaml)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        # Create default config file
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG)
        print(f"Created default configuration file: {config_file}")

    with open(config_file, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_api_settings() -> APISettings:
    """Get cached API settings instance"""
    # Load timezone from config.yaml if available
    config = load_yaml_config()
    app_config = config.get("application", {})
    timezone = app_config.get("timezone", "UTC")

    return APISettings(timezone=timezone)


@lru_cache
def get_db_settings() -> GlassTraxDBSettings:
    """Get cached database settings instance"""
    # Load friendly_name from config.yaml if available
    config = load_yaml_config()
    db_config = config.get("database", {})
    friendly_name = db_config.get("friendly_name", "GlassTrax Database")

    return GlassTraxDBSettings(friendly_name=friendly_name)


class AdminSettings:
    """Admin authentication settings loaded from config.yaml"""

    def __init__(self):
        config = load_yaml_config()
        admin_config = config.get("admin", {})

        self.username: str = admin_config.get("username", "admin")
        self.password_hash: str | None = admin_config.get("password_hash")

        # If no password hash set, create a default one (for initial setup)
        if not self.password_hash:
            # Default password is 'admin' - should be changed!
            self.password_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()
            self._is_default = True
        else:
            self._is_default = False

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    @property
    def is_default_password(self) -> bool:
        """Check if using default password (should prompt to change)"""
        return self._is_default


def get_admin_settings() -> AdminSettings:
    """Get admin settings instance (not cached - reloads from config)"""
    return AdminSettings()


def hash_password(password: str) -> str:
    """Hash a password for storage in config.yaml"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
