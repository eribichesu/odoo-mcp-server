#!/usr/bin/env python3
"""
CLI script to run the Odoo MCP server.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from odoo_mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())