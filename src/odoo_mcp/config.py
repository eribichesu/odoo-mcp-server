"""
Configuration management for the Odoo MCP server.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
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
        description="Odoo username or email (used by the XML-RPC transport)",
    )
    odoo_password: str = Field(
        ...,  # Required
        description="Odoo password or API key (used by the XML-RPC transport)",
    )

    # Authentication / transport
    odoo_api_key: Optional[str] = Field(
        default=None,
        description=(
            "Odoo API key. Required for the JSON-2 transport (Odoo 19+) and "
            "recommended for XML-RPC when two-factor authentication is enabled. "
            "Generate one under Preferences > Account Security > New API Key."
        ),
    )
    odoo_transport: str = Field(
        default="auto",
        description=(
            "Which external API to use: 'auto' (JSON-2 when an API key is set, "
            "otherwise XML-RPC), 'json2' (Odoo 19+ /json/2 endpoint), or "
            "'xmlrpc' (legacy /xmlrpc/2, deprecated in Odoo 19)."
        ),
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
        default="0.2.0",
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