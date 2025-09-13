# Claude Desktop Configuration Guide

## 📋 Step-by-Step Setup

### 1. Locate Claude Desktop Configuration File

The configuration file location depends on your operating system:

**macOS (your system):**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### 2. Open/Create the Configuration File

If the file doesn't exist, create it. If it exists, you'll need to merge the configuration.

### 3. Add Odoo MCP Server Configuration

**Option A: If the file is empty or doesn't exist**
Copy the entire contents from `claude-desktop-config.json` in this project.

**Option B: If you already have other MCP servers configured**
Add just the "odoo" section to your existing "mcpServers" object:

```json
{
  "mcpServers": {
    "your-existing-server": {
      // ... your existing config
    },
    "odoo": {
      "command": "python",
      "args": ["/Users/edoardo.ribichesu/vscode/odoo.mcp/src/odoo_mcp/server.py"],
      "env": {
        "PYTHONPATH": "/Users/edoardo.ribichesu/vscode/odoo.mcp/src"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

After saving the configuration file, completely quit and restart Claude Desktop.

### 5. Verify Connection

Once Claude Desktop restarts, you should see the Odoo MCP server available. You can test it by asking:

- "What MCP tools are available?"
- "Search for customers in Odoo"
- "Show me the fields available in the res.partner model"

## 🔧 Configuration Details

**Command:** `python` - Uses the system Python
**Args:** Path to your MCP server script
**Environment:** Sets PYTHONPATH so imports work correctly

## 🚨 Important Notes

1. **Python Environment**: The configuration assumes your virtual environment Python is accessible as `python`. If not, you may need to use the full path:
   ```json
   "command": "/Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python"
   ```

2. **Environment Variables**: Your `.env` file must be in the project root for the server to find your Odoo credentials.

3. **Permissions**: Make sure Claude Desktop has permission to execute Python scripts.

## 🧪 Testing

After setup, try these commands in Claude Desktop:

- "List the available MCP tools"
- "Search for the first 3 customers in Odoo"
- "What fields are available in the product.product model?"
- "Create a test contact in Odoo"

## 🔍 Troubleshooting

If the connection fails:

1. Check that the Python path is correct
2. Verify your `.env` file is properly configured
3. Test the server manually: `cd /Users/edoardo.ribichesu/vscode/odoo.mcp && .venv/bin/activate && python src/odoo_mcp/server.py`
4. Check Claude Desktop logs for error messages

---

**Ready to connect Claude Desktop to your Odoo instance! 🎉**