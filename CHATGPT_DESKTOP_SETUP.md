# ChatGPT Desktop - Odoo MCP Server Configuration

## 🔌 Configuring Odoo MCP Server for ChatGPT Desktop

ChatGPT Desktop supports MCP servers through extension configuration. Here's how to set up your Odoo MCP server.

### 📋 Configuration Options

ChatGPT Desktop typically uses one of these approaches for MCP server integration:

#### Option 1: Direct Extension Configuration

Create a configuration file for ChatGPT Desktop:

**File:** `~/.config/chatgpt-desktop/mcp-config.json`

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python",
      "args": ["/Users/edoardo.ribichesu/vscode/odoo.mcp/src/odoo_mcp/server.py"],
      "cwd": "/Users/edoardo.ribichesu/vscode/odoo.mcp",
      "env": {
        "PYTHONPATH": "/Users/edoardo.ribichesu/vscode/odoo.mcp/src"
      }
    }
  }
}
```

#### Option 2: Extension Manifest

Create an extension manifest file:

**File:** `odoo-mcp-extension.json`

```json
{
  "name": "Odoo MCP Server",
  "version": "1.0.0",
  "description": "MCP server for Odoo integration - CRUD operations, model introspection, and reporting",
  "author": "Your Name",
  "mcp": {
    "server": {
      "command": "/Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python",
      "args": ["/Users/edoardo.ribichesu/vscode/odoo.mcp/src/odoo_mcp/server.py"],
      "cwd": "/Users/edoardo.ribichesu/vscode/odoo.mcp",
      "env": {
        "PYTHONPATH": "/Users/edoardo.ribichesu/vscode/odoo.mcp/src"
      }
    },
    "tools": [
      {
        "name": "check_odoo_connection",
        "description": "Check connection to Odoo server"
      },
      {
        "name": "search_odoo_records", 
        "description": "Search for records in Odoo models"
      },
      {
        "name": "create_odoo_record",
        "description": "Create new records in Odoo"
      },
      {
        "name": "update_odoo_record",
        "description": "Update existing Odoo records"
      },
      {
        "name": "delete_odoo_record", 
        "description": "Delete records from Odoo"
      },
      {
        "name": "get_odoo_model_fields",
        "description": "Get field definitions for Odoo models"
      }
    ]
  }
}
```

### 🚀 Setup Instructions

1. **Check ChatGPT Desktop MCP Support**
   - Open ChatGPT Desktop settings
   - Look for "Extensions", "Plugins", or "MCP Servers" section
   - Note the configuration method used

2. **Create Configuration Directory** (if needed)
   ```bash
   mkdir -p ~/.config/chatgpt-desktop
   ```

3. **Copy Configuration File**
   ```bash
   cp odoo-mcp-chatgpt-config.json ~/.config/chatgpt-desktop/mcp-config.json
   ```

4. **Restart ChatGPT Desktop**

5. **Test Connection**
   - Ask: "What MCP tools are available?"
   - Ask: "Check my Odoo connection"
   - Ask: "Search for customers in Odoo"

### 🔧 Alternative: Standalone MCP Extension

If ChatGPT Desktop doesn't have built-in MCP support, you can create a bridge extension:

**File:** `chatgpt-odoo-bridge.py`

```python
#!/usr/bin/env python3
"""
Bridge extension for ChatGPT Desktop to connect to Odoo MCP server.
"""

import asyncio
import json
import subprocess
from typing import Dict, Any

class ChatGPTOdooBridge:
    def __init__(self):
        self.mcp_server_path = "/Users/edoardo.ribichesu/vscode/odoo.mcp/src/odoo_mcp/server.py"
        self.python_path = "/Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python"
        self.working_dir = "/Users/edoardo.ribichesu/vscode/odoo.mcp"
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return the result."""
        # Implementation would depend on ChatGPT Desktop's extension API
        pass
    
    def get_available_tools(self) -> list:
        """Return list of available Odoo MCP tools."""
        return [
            "check_odoo_connection",
            "search_odoo_records", 
            "create_odoo_record",
            "update_odoo_record",
            "delete_odoo_record",
            "get_odoo_model_fields"
        ]

# Extension registration (format depends on ChatGPT Desktop)
def register_extension():
    return ChatGPTOdooBridge()
```

### 📱 ChatGPT Desktop Specific Steps

Since ChatGPT Desktop's MCP integration may vary, here are the general steps:

1. **Check Documentation**: Look for ChatGPT Desktop's official MCP/extension documentation
2. **Configuration Location**: Find where ChatGPT Desktop stores extension configs
3. **Format Requirements**: Determine the exact JSON format required
4. **Installation Method**: Some may require placing files in specific directories

### 🔍 Troubleshooting

**Issue:** ChatGPT Desktop doesn't recognize the MCP server
**Solution:** 
- Check the configuration file location
- Verify the JSON format matches ChatGPT Desktop's requirements
- Ensure Python path and working directory are correct

**Issue:** "Permission denied" errors
**Solution:**
```bash
chmod +x /Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python
```

**Issue:** Environment variables not loading
**Solution:** Verify the `cwd` is set to the project root where `.env` file exists

### 📞 Need Help?

If you need specific guidance for your ChatGPT Desktop version, please share:
1. ChatGPT Desktop version
2. Available extension/MCP configuration options in settings
3. Any error messages you encounter

---

**Your Odoo MCP server is ready - just need to configure ChatGPT Desktop to connect to it!**