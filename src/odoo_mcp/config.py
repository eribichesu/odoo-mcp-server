"""
Configuration management for the Odoo MCP server.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

from typing import Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class OdooSettings(BaseSettings):
    """Settings for Odoo connection."""

    model_config = SettingsConfigDict(
        env_prefix="ODOO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Odoo connection settings
    url: HttpUrl = Field(
        ...,
        description="Odoo server URL (e.g., https://your-instance.odoo.com)",
    )
    database: str = Field(
        ...,
        description="Odoo database name",
    )
    username: str = Field(
        ...,
        description="Odoo username",
    )
    password: str = Field(
        ...,
        description="Odoo password or API key",
    )

    # Optional settings
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests",
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retries in seconds",
    )

    # MCP server settings
    server_name: str = Field(
        default="odoo-mcp",
        description="MCP server name",
    )
    server_version: str = Field(
        default="0.1.0",
        description="MCP server version",
    )

    # Default limits for operations
    default_limit: int = Field(
        default=100,
        description="Default limit for search operations",
    )
    max_limit: int = Field(
        default=1000,
        description="Maximum limit for search operations",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Debug mode
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Odoo connection settings
    odoo_url: str = Field(
        ...,  # Required
        description="Odoo instance URL (e.g., https://mycompany.odoo.com)",
    )
    odoo_database: str = Field(
        ...,  # Required
        description="Odoo database name",
    )
    odoo_username: str = Field(
        ...,  # Required
        description="Odoo username or email",
    )
    odoo_password: str = Field(
        ...,  # Required
        description="Odoo password or API key",
    )

    # Optional Odoo settings
    odoo_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
    )
    odoo_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests",
    )
    odoo_retry_delay: float = Field(
        default=1.0,
        description="Delay between retries in seconds",
    )

    # MCP server settings
    server_name: str = Field(
        default="odoo-mcp",
        description="MCP server name",
    )
    server_version: str = Field(
        default="0.1.0",
        description="MCP server version",
    )

    # Default limits for operations
    default_limit: int = Field(
        default=100,
        description="Default limit for search operations",
    )
    max_limit: int = Field(
        default=1000,
        description="Maximum limit for search operations",
    )


# Global settings instance (lazy-loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings