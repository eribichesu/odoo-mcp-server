"""
Odoo MCP Server

A Model Context Protocol server for Odoo integration. Talks to Odoo over the
JSON-2 API (Odoo 19+) or the legacy XML-RPC API, selected via configuration.
"""

__version__ = "0.2.0"
__author__ = "Edoardo Ribichesu"

from .client import OdooClient
from .config import Settings, get_settings
from .errors import (
    OdooError,
    OdooAuthenticationError,
    OdooConnectionError,
    OdooRequestError,
)

# Make app available for import but don't load it automatically
def get_app():
    """Get the FastMCP application instance."""
    from .server import app
    return app

__all__ = [
    "OdooClient",
    "Settings",
    "get_settings",
    "get_app",
    "OdooError",
    "OdooAuthenticationError",
    "OdooConnectionError",
    "OdooRequestError",
]