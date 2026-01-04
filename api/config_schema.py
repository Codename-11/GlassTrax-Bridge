"""
Config Schema Validation

Pydantic models for validating config.yaml structure.
Provides clear error messages when configuration is invalid.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DatabaseConfig(BaseModel):
    """GlassTrax database connection configuration"""

    friendly_name: str = Field(
        default="GlassTrax Database",
        description="Display name shown in the UI",
    )
    dsn: str = Field(
        default="LIVE",
        min_length=1,
        description="ODBC Data Source Name (configured in Windows ODBC Administrator)",
    )
    readonly: bool = Field(default=True, description="Connect in read-only mode")
    timeout: int = Field(default=30, ge=1, le=300, description="Query timeout in seconds")

    @field_validator("readonly")
    @classmethod
    def warn_if_not_readonly(cls, v: bool) -> bool:
        """Warn if readonly is set to False"""
        if not v:
            import warnings

            warnings.warn(
                "SECURITY WARNING: readonly=false allows writes to GlassTrax database!",
                UserWarning,
                stacklevel=2,
            )
        return v


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_to_console: bool = Field(default=True, description="Enable console logging")


class PerformanceConfig(BaseModel):
    """Performance tuning configuration"""

    query_timeout: int = Field(default=60, ge=1, le=600, description="Query timeout in seconds")
    fetch_size: int = Field(default=100, ge=100, le=10000, description="Rows to fetch at once")


class ApplicationConfig(BaseModel):
    """Application settings"""

    timezone: str = Field(
        default="UTC",
        description="IANA timezone name (e.g., America/New_York)",
    )
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is a known IANA timezone"""
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(v)
        except Exception:
            raise ValueError(
                f"Invalid timezone '{v}'. Use IANA format like 'America/New_York' or 'UTC'"
            )
        return v


class FeaturesConfig(BaseModel):
    """Feature flags (NOT YET IMPLEMENTED - see TODO.md)"""

    enable_caching: bool = Field(default=False, description="NOT IMPLEMENTED: Query result caching")
    enable_exports: bool = Field(default=True, description="NOT IMPLEMENTED: Data export functionality")


class AdminConfig(BaseModel):
    """Admin portal authentication"""

    username: str = Field(default="admin", min_length=1, description="Admin username")
    password_hash: Optional[str] = Field(
        default=None,
        description="bcrypt password hash (leave empty for default 'admin')",
    )


class AgentConfig(BaseModel):
    """GlassTrax Agent connection configuration"""

    enabled: bool = Field(
        default=False,
        description="Use GlassTrax Agent for database queries (required in Docker)",
    )
    url: str = Field(
        default="http://localhost:8001",
        description="Agent URL (http://host:port)",
    )
    api_key: str = Field(
        default="",
        description="Agent API key for authentication",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )


class AppConfig(BaseModel):
    """
    Root configuration model for config.yaml

    Validates the entire configuration structure on load.
    """

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)

    model_config = {"populate_by_name": True}


def validate_config(config_dict: dict) -> AppConfig:
    """
    Validate a config dictionary against the schema.

    Args:
        config_dict: Raw dictionary loaded from config.yaml

    Returns:
        Validated AppConfig instance

    Raises:
        pydantic.ValidationError: If config is invalid
    """
    return AppConfig.model_validate(config_dict)


def get_validation_errors(config_dict: dict) -> List[str]:
    """
    Get a list of validation errors for a config dictionary.

    Args:
        config_dict: Raw dictionary loaded from config.yaml

    Returns:
        List of error messages (empty if valid)
    """
    try:
        validate_config(config_dict)
        return []
    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError):
            return [
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in e.errors()
            ]
        return [str(e)]


# Editable config schema (matches UI's ConfigData type)
class EditableLoggingConfig(BaseModel):
    """Logging config for UI"""
    level: str
    log_to_file: bool
    log_to_console: bool


class EditablePerformanceConfig(BaseModel):
    """Performance config for UI"""
    query_timeout: int
    fetch_size: int


class EditableDatabaseConfig(BaseModel):
    """Database config for UI editing"""
    friendly_name: str
    dsn: str = Field(min_length=1)
    readonly: bool
    timeout: int = Field(ge=1, le=300)


class EditableApplicationConfig(BaseModel):
    """Application config for UI editing"""
    timezone: str
    logging: EditableLoggingConfig
    performance: EditablePerformanceConfig

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is a known IANA timezone"""
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            raise ValueError(
                f"Invalid timezone '{v}'. Use IANA format like 'America/New_York' or 'UTC'"
            )
        return v


class EditableFeaturesConfig(BaseModel):
    """Features config for UI editing"""
    enable_caching: bool
    enable_exports: bool


class EditableAdminConfig(BaseModel):
    """Admin config for UI editing"""
    username: str = Field(min_length=1)


class EditableAgentConfig(BaseModel):
    """Agent config for UI editing"""
    enabled: bool
    url: str
    api_key: str
    timeout: int = Field(ge=1, le=300)


class EditableConfig(BaseModel):
    """
    Config schema matching the UI's ConfigData type.

    Used to validate updates from the Settings page.
    """
    database: EditableDatabaseConfig
    application: EditableApplicationConfig
    features: EditableFeaturesConfig
    admin: EditableAdminConfig
    agent: EditableAgentConfig


def validate_editable_config(config_dict: dict) -> EditableConfig:
    """
    Validate an editable config update from the UI.

    Args:
        config_dict: Config dict from UI (matches ConfigData type)

    Returns:
        Validated EditableConfig instance

    Raises:
        pydantic.ValidationError: If config is invalid
    """
    return EditableConfig.model_validate(config_dict)
