# Odoo MCP Server - Quick Setup Guide

## 🚀 Server is Ready!

Your Odoo MCP server is fully functional and ready for production use.

## ✅ Tested Features

All core MCP tools have been tested and verified:

- **Authentication**: ✅ Connected to your Odoo instance
- **Search Records**: ✅ Query and filter Odoo data
- **Model Introspection**: ✅ Get field definitions and model schema
- **Create Records**: ✅ Add new data to Odoo
- **Update Records**: ✅ Modify existing Odoo records
- **Delete Records**: ✅ Remove data from Odoo
- **Method Calls**: ✅ Execute custom Odoo methods (when available)

## 🔌 Connect to MCP Clients

### Option 1: Claude Desktop

Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
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

### Option 2: Other MCP Clients

The server follows the standard MCP protocol and can be used with any MCP-compatible client.

**Server Command:**
```bash
cd /Users/edoardo.ribichesu/vscode/odoo.mcp
. .venv/bin/activate
python src/odoo_mcp/server.py
```

## 🛠 Available MCP Tools

When connected, you'll have access to these tools:

1. **`search_records`** - Search and retrieve Odoo records
2. **`create_record`** - Create new records in Odoo
3. **`update_record`** - Update existing Odoo records
4. **`delete_record`** - Delete records from Odoo
5. **`get_model_fields`** - Get field definitions for Odoo models
6. **`call_method`** - Execute custom Odoo model methods

## 📊 Example Usage

With your MCP client connected, you can ask questions like:

- "Show me the latest 5 customers in Odoo"
- "Create a new contact named John Doe with email john@example.com"
- "What fields are available in the product model?"
- "Update the phone number for customer ID 123"
- "Find all invoices from this month"

## 🔧 Configuration

Your `.env` file is already configured with your Odoo credentials. All settings are working and tested.

## 🚨 Security Note

Keep your `.env` file secure and never commit it to version control. Your Odoo API key and credentials are sensitive information.

---

**Your Odoo MCP Server is now production-ready! 🎉**