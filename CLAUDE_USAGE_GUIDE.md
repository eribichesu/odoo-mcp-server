# Claude Desktop - Odoo MCP Tools Usage Guide

## 🎯 How to Use Odoo MCP Tools in Claude Desktop

### ✅ Available Tools

1. **check_odoo_connection** - Test Odoo server connection
2. **search_odoo_records** - Search for records in Odoo models
3. **create_odoo_record** - Create new records in Odoo
4. **update_odoo_record** - Update existing Odoo records  
5. **delete_odoo_record** - Delete records from Odoo
6. **get_odoo_model_fields** - Get field definitions for models

### 🔧 Important Usage Notes

#### Domain Parameter Format
When using `search_odoo_records`, the `domain` parameter must be a **JSON string**, not a list:

✅ **Correct:**
```
domain: "[["is_company", "=", true], ["supplier_rank", ">", 0]]"
```

❌ **Incorrect:**
```
domain: [["is_company", "=", true], ["supplier_rank", ">", 0]]
```

#### Fields Parameter Format
The `fields` parameter should be a **comma-separated string**:

✅ **Correct:**
```
fields: "name,email,phone,create_date,supplier_rank"
```

❌ **Incorrect:**
```
fields: ["name", "email", "phone", "create_date", "supplier_rank"]
```

### 📋 Example Commands for Claude

**Search for companies:**
```
Use search_odoo_records with:
- model: "res.partner" 
- domain: "[["is_company", "=", true]]"
- fields: "name,email,phone"
- limit: 10
```

**Search with multiple conditions:**
```
Use search_odoo_records with:
- model: "res.partner"
- domain: "[["is_company", "=", true], ["supplier_rank", ">", 0]]"
- fields: "name,email,phone,supplier_rank"
- limit: 5
- order: "create_date DESC"
```

**Check connection:**
```
Use check_odoo_connection (no parameters needed)
```

**Get model information:**
```
Use get_odoo_model_fields with:
- model: "res.partner"
```

### 🚨 Common Issues & Solutions

**Issue:** "Input should be a valid string" error for domain
**Solution:** Make sure domain is passed as a JSON string, not a Python list

**Issue:** "OdooClient object has no attribute" errors  
**Solution:** ✅ Fixed in latest version - restart Claude Desktop

**Issue:** "Server disconnected"
**Solution:** ✅ Fixed in latest version - restart Claude Desktop

### 🎉 Ready to Use!

Your Odoo MCP server is now properly configured and all connection issues have been resolved. You can now interact with your Odoo instance using natural language through Claude Desktop!