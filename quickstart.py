#!/usr/bin/env python3
"""
Quick start script for development - sets up test environment and runs the server.
"""

import os
import sys

# Set up test environment variables if not already set
test_env = {
    "ODOO_URL": "https://demo.odoo.com",
    "ODOO_DATABASE": "demo",
    "ODOO_USERNAME": "demo",
    "ODOO_PASSWORD": "demo",
    "LOG_LEVEL": "DEBUG",
}

for key, value in test_env.items():
    if key not in os.environ:
        os.environ[key] = value
        print(f"Set {key}={value}")

# Now import and run the server
try:
    from odoo_mcp import get_app
    import asyncio
    
    print("\nStarting Odoo MCP Server with demo configuration...")
    print("Note: This uses demo credentials - update .env for production use")
    print("\nTo test the server, you can connect using MCP client tools.")
    print("Press Ctrl+C to stop the server.")
    
    app = get_app()
    
    # This would typically be run by MCP infrastructure
    print("\nServer initialized successfully!")
    print("In production, this would be started by the MCP client.")
    
except ImportError as e:
    print(f"Error importing odoo_mcp: {e}")
    print("Make sure to install the package with: pip install -e .")
    sys.exit(1)
except Exception as e:
    print(f"Error starting server: {e}")
    sys.exit(1)