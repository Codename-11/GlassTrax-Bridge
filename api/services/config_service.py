### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Configuration Service -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Configuration Service

Provides read/write access to config.yaml while preserving comments and formatting.
Uses ruamel.yaml for comment-preserving YAML operations.
Includes Pydantic validation for config structure.

Config file location is determined by api.config.get_config_path():
1. GLASSTRAX_CONFIG_PATH environment variable (if set)
2. data/config.yaml (default - persisted in Docker via volume mount)
3. config.yaml in project root (legacy fallback)
"""

import builtins
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from api.config import DEFAULT_CONFIG, get_config_path
from api.config_schema import (
    get_validation_errors,
    validate_editable_config,
)


class ConfigService:
    """
    Service for managing config.yaml with comment preservation.

    Uses ruamel.yaml to load and save YAML while keeping all comments,
    formatting, and structure intact.
    """

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            self.config_path = get_config_path()
        else:
            self.config_path = Path(config_path)
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self._config: CommentedMap | None = None

        # Create default config if missing
        self._ensure_config_exists()

    def _ensure_config_exists(self) -> None:
        """Create default config file if it doesn't exist"""
        if not self.config_path.exists():
            # Ensure parent directory exists (for data/config.yaml)
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create default config file
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_CONFIG)
            print(f"Created default configuration file: {self.config_path}")

    def _ensure_loaded(self) -> CommentedMap:
        """Ensure config is loaded, load if not"""
        if self._config is None:
            self.reload()
        return self._config

    def reload(self, validate: bool = True) -> CommentedMap:
        """
        Reload config from disk.

        Args:
            validate: If True, validate config against schema on load

        Raises:
            pydantic.ValidationError: If config is invalid and validate=True
        """
        # Ensure config exists (creates default if missing)
        self._ensure_config_exists()

        with open(self.config_path, encoding='utf-8') as f:
            self._config = self.yaml.load(f)

        # Validate against schema
        if validate:
            errors = get_validation_errors(dict(self._config) if self._config else {})
            if errors:
                # Log warnings but don't fail - allows partial configs
                import warnings
                for error in errors:
                    warnings.warn(f"Config validation warning: {error}", UserWarning, stacklevel=2)

        return self._config

    def save(self) -> None:
        """Save config to disk, preserving comments and formatting"""
        if self._config is None:
            raise ValueError("No config loaded to save")

        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.yaml.dump(self._config, f)

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a config value by dot-notation path.

        Example: get("database.friendly_name") -> "TGI Database"
        """
        config = self._ensure_loaded()
        keys = path.split('.')
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, path: str, value: Any) -> None:
        """
        Set a config value by dot-notation path.

        Example: set("database.timeout", 60)
        """
        config = self._ensure_loaded()
        keys = path.split('.')

        # Navigate to parent
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = CommentedMap()
            current = current[key]

        # Set the value
        current[keys[-1]] = value

    def get_section(self, section: str) -> dict:
        """Get an entire config section as a dict"""
        config = self._ensure_loaded()
        return dict(config.get(section, {}))

    def get_editable_config(self) -> dict:
        """
        Get config suitable for UI editing.

        Returns a sanitized dict with only editable fields,
        excluding sensitive data like password hashes.
        The returned dict matches the UI's ConfigData TypeScript type.
        """
        self._ensure_loaded()

        return {
            "database": {
                "friendly_name": self.get("database.friendly_name", "GlassTrax Database"),
                "dsn": self.get("database.dsn", "LIVE"),
                "readonly": self.get("database.readonly", True),
                "timeout": self.get("database.timeout", 30),
            },
            "application": {
                "timezone": self.get("application.timezone", "America/New_York"),
                "logging": {
                    "level": self.get("application.logging.level", "INFO"),
                    "log_to_file": self.get("application.logging.log_to_file", True),
                    "log_to_console": self.get("application.logging.log_to_console", True),
                },
                "performance": {
                    "query_timeout": self.get("application.performance.query_timeout", 60),
                    "fetch_size": self.get("application.performance.fetch_size", 1000),
                },
            },
            "features": {
                "enable_caching": self.get("features.enable_caching", False),
                "enable_exports": self.get("features.enable_exports", True),
            },
            "caching": {
                "fabs_ttl_minutes": self.get("caching.fabs_ttl_minutes", 30),
                "max_cached_dates": self.get("caching.max_cached_dates", 7),
            },
            "admin": {
                "username": self.get("admin.username", "admin"),
                # Note: password_hash is intentionally excluded
            },
            "agent": {
                "enabled": self.get("agent.enabled", False),
                "url": self.get("agent.url", "http://localhost:8001"),
                "api_key": self.get("agent.api_key", ""),
                "timeout": self.get("agent.timeout", 30),
            },
        }

    def validate_update(self, updates: dict) -> list[str]:
        """
        Validate an update dict before applying.

        Args:
            updates: Partial config update from UI

        Returns:
            List of validation error messages (empty if valid)
        """
        # Build a full config by merging current with updates
        current = self.get_editable_config()

        # Deep merge updates into current
        def deep_merge(base: dict, update: dict) -> dict:
            result = base.copy()
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        merged = deep_merge(current, updates)

        # Validate the merged config
        try:
            validate_editable_config(merged)
            return []
        except Exception as e:
            from pydantic import ValidationError
            if isinstance(e, ValidationError):
                return [
                    f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                    for err in e.errors()
                ]
            return [str(e)]

    def update_from_dict(self, updates: dict, prefix: str = "") -> list[str]:
        """
        Update config from a nested dict, returning list of changed paths.

        Only updates values that have actually changed.
        """
        changed = []

        for key, value in updates.items():
            path = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recurse into nested dicts
                changed.extend(self.update_from_dict(value, path))
            else:
                # Check if value changed
                current = self.get(path)
                if current != value:
                    self.set(path, value)
                    changed.append(path)

        return changed

    def get_restart_required_fields(self) -> builtins.set[str]:
        """Fields that require a server restart to take effect"""
        return {
            "database.dsn",  # Changing DSN requires reconnection
        }

    def get_hot_reload_fields(self) -> builtins.set[str]:
        """Fields that can be hot-reloaded without restart"""
        return {
            "database.friendly_name",
            "database.timeout",
            "database.readonly",
            "application.timezone",
            "application.logging.level",
            "application.logging.log_to_file",
            "application.logging.log_to_console",
            "application.performance.query_timeout",
            "application.performance.fetch_size",
            "features.enable_caching",
            "features.enable_exports",
            "admin.username",
            # Agent settings - can be hot-reloaded
            "agent.enabled",
            "agent.url",
            "agent.api_key",
            "agent.timeout",
        }


# Singleton instance
_config_service: ConfigService | None = None


def get_config_service() -> ConfigService:
    """Get the singleton config service instance"""
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


def clear_config_cache() -> None:
    """Clear the config service cache (forces reload on next access)"""
    global _config_service
    if _config_service is not None:
        _config_service._config = None
