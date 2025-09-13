"""
Odoo MCP Server

A Model Context Protocol server for Odoo integration that provides tools for 
interacting with Odoo online instances via XML-RPC API.
"""

__version__ = "0.1.0"
__author__ = "Edoardo Ribichesu"

from .client import OdooClient
from .config import Settings, get_settings

# Make app available for import but don't load it automatically
def get_app():
    """Get the FastMCP application instance."""
    from .server import app
    return app

__all__ = ["OdooClient", "Settings", "get_settings", "get_app"]