"""
Main MCP server impl# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create the FastMCP app
app = FastMCP(settings.server_name)n for Odoo integration.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, Tool

from .client import OdooClient, OdooError
from .config import get_settings
from .tools import (
    create_record_tool,
    delete_record_tool,
    get_model_fields_tool,
    search_records_tool,
    update_record_tool,
    call_method_tool,
)


# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create the FastMCP server  
app = FastMCP(settings.server_name)

# Global Odoo client instance
_odoo_client: Optional[OdooClient] = None


async def get_odoo_client() -> OdooClient:
    """Get or create the global Odoo client instance."""
    global _odoo_client
    
    if _odoo_client is None:
        _odoo_client = OdooClient(settings)
        
    return _odoo_client


@app.tool()
async def check_odoo_connection() -> str:
    """
    Check the connection to the Odoo server and return status information.
    
    Returns:
        JSON string with connection status and server information
    """
    try:
        client = await get_odoo_client()
        connection_info = await client.check_connection()
        
        return json.dumps(connection_info, indent=2)
        
    except Exception as e:
        logger.error(f"Connection check failed: {e}")
        return json.dumps({
            "connected": False,
            "error": str(e),
        }, indent=2)


@app.tool()
async def search_odoo_records(
    model: str,
    domain: Optional[str] = None,
    fields: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order: Optional[str] = None,
) -> str:
    """
    Search for records in an Odoo model.
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        domain: Search domain as JSON string (e.g., '[["name", "ilike", "customer"]]')
        fields: Comma-separated list of fields to retrieve (e.g., 'name,email,phone')
        limit: Maximum number of records to return (default: 100, max: 1000)
        offset: Number of records to skip (default: 0)
        order: Sort order (e.g., 'name ASC', 'create_date DESC')
    
    Returns:
        JSON string with search results
    """
    try:
        client = await get_odoo_client()
        
        # Parse domain from JSON string
        parsed_domain = None
        if domain:
            try:
                parsed_domain = json.loads(domain)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"Invalid domain JSON: {e}"
                }, indent=2)
        
        # Parse fields
        parsed_fields = None
        if fields:
            parsed_fields = [f.strip() for f in fields.split(",")]
        
        # Search records
        records = await client.search_records(
            model=model,
            domain=parsed_domain,
            fields=parsed_fields,
            limit=limit,
            offset=offset,
            order=order,
        )
        
        return json.dumps({
            "model": model,
            "count": len(records),
            "records": records,
        }, indent=2, default=str)
        
    except OdooError as e:
        logger.error(f"Odoo error in search_records: {e}")
        return json.dumps({
            "error": f"Odoo error: {e}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in search_records: {e}")
        return json.dumps({
            "error": f"Unexpected error: {e}"
        }, indent=2)


@app.tool()
async def create_odoo_record(
    model: str,
    values: str,
) -> str:
    """
    Create a new record in an Odoo model.
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        values: Record values as JSON string (e.g., '{"name": "New Customer", "email": "customer@example.com"}')
    
    Returns:
        JSON string with the created record ID
    """
    try:
        client = await get_odoo_client()
        
        # Parse values from JSON string
        try:
            parsed_values = json.loads(values)
        except json.JSONDecodeError as e:
            return json.dumps({
                "error": f"Invalid values JSON: {e}"
            }, indent=2)
        
        # Create record
        record_id = await client.create_record(model, parsed_values)
        
        return json.dumps({
            "model": model,
            "record_id": record_id,
            "values": parsed_values,
            "success": True,
        }, indent=2)
        
    except OdooError as e:
        logger.error(f"Odoo error in create_record: {e}")
        return json.dumps({
            "error": f"Odoo error: {e}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in create_record: {e}")
        return json.dumps({
            "error": f"Unexpected error: {e}"
        }, indent=2)


@app.tool()
async def update_odoo_record(
    model: str,
    record_id: int,
    values: str,
) -> str:
    """
    Update an existing record in an Odoo model.
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        record_id: ID of the record to update
        values: Updated values as JSON string (e.g., '{"name": "Updated Name", "email": "new@example.com"}')
    
    Returns:
        JSON string with update status
    """
    try:
        client = await get_odoo_client()
        
        # Parse values from JSON string
        try:
            parsed_values = json.loads(values)
        except json.JSONDecodeError as e:
            return json.dumps({
                "error": f"Invalid values JSON: {e}"
            }, indent=2)
        
        # Update record
        success = await client.update_record(model, record_id, parsed_values)
        
        return json.dumps({
            "model": model,
            "record_id": record_id,
            "values": parsed_values,
            "success": success,
        }, indent=2)
        
    except OdooError as e:
        logger.error(f"Odoo error in update_record: {e}")
        return json.dumps({
            "error": f"Odoo error: {e}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in update_record: {e}")
        return json.dumps({
            "error": f"Unexpected error: {e}"
        }, indent=2)


@app.tool()
async def delete_odoo_record(
    model: str,
    record_id: int,
) -> str:
    """
    Delete a record from an Odoo model.
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        record_id: ID of the record to delete
    
    Returns:
        JSON string with deletion status
    """
    try:
        client = await get_odoo_client()
        
        # Delete record
        success = await client.delete_record(model, record_id)
        
        return json.dumps({
            "model": model,
            "record_id": record_id,
            "success": success,
        }, indent=2)
        
    except OdooError as e:
        logger.error(f"Odoo error in delete_record: {e}")
        return json.dumps({
            "error": f"Odoo error: {e}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in delete_record: {e}")
        return json.dumps({
            "error": f"Unexpected error: {e}"
        }, indent=2)


@app.tool()
async def get_odoo_model_fields(model: str) -> str:
    """
    Get field definitions for an Odoo model.
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
    
    Returns:
        JSON string with field definitions
    """
    try:
        client = await get_odoo_client()
        
        # Get model fields
        fields = await client.get_model_fields(model)
        
        return json.dumps({
            "model": model,
            "fields": fields,
        }, indent=2, default=str)
        
    except OdooError as e:
        logger.error(f"Odoo error in get_model_fields: {e}")
        return json.dumps({
            "error": f"Odoo error: {e}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in get_model_fields: {e}")
        return json.dumps({
            "error": f"Unexpected error: {e}"
        }, indent=2)


@app.tool()
async def call_odoo_method(
    model: str,
    method: str,
    args: Optional[str] = None,
    kwargs: Optional[str] = None,
) -> str:
    """
    Call a custom method on an Odoo model.
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        method: Method name to call
        args: Positional arguments as JSON string (e.g., '[1, 2, 3]')
        kwargs: Keyword arguments as JSON string (e.g., '{"context": {"lang": "en_US"}}')
    
    Returns:
        JSON string with method result
    """
    try:
        client = await get_odoo_client()
        
        # Parse arguments
        parsed_args = []
        if args:
            try:
                parsed_args = json.loads(args)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"Invalid args JSON: {e}"
                }, indent=2)
        
        parsed_kwargs = {}
        if kwargs:
            try:
                parsed_kwargs = json.loads(kwargs)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"Invalid kwargs JSON: {e}"
                }, indent=2)
        
        # Call method
        result = await client.call_method(model, method, parsed_args, parsed_kwargs)
        
        return json.dumps({
            "model": model,
            "method": method,
            "result": result,
        }, indent=2, default=str)
        
    except OdooError as e:
        logger.error(f"Odoo error in call_method: {e}")
        return json.dumps({
            "error": f"Odoo error: {e}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in call_method: {e}")
        return json.dumps({
            "error": f"Unexpected error: {e}"
        }, indent=2)


# Resources for model information and examples
@app.resource("odoo://models/common")
def get_common_models() -> str:
    """Get information about commonly used Odoo models."""
    common_models = {
        "res.partner": {
            "description": "Customers, vendors, and contacts",
            "key_fields": ["name", "email", "phone", "is_company", "customer_rank", "supplier_rank"],
            "example_domain": '[["customer_rank", ">", 0]]',
        },
        "sale.order": {
            "description": "Sales orders",
            "key_fields": ["name", "partner_id", "date_order", "amount_total", "state"],
            "example_domain": '[["state", "in", ["sale", "done"]]]',
        },
        "purchase.order": {
            "description": "Purchase orders",
            "key_fields": ["name", "partner_id", "date_order", "amount_total", "state"],
            "example_domain": '[["state", "in", ["purchase", "done"]]]',
        },
        "product.product": {
            "description": "Products and variants",
            "key_fields": ["name", "default_code", "list_price", "standard_price", "type"],
            "example_domain": '[["sale_ok", "=", True]]',
        },
        "product.template": {
            "description": "Product templates",
            "key_fields": ["name", "default_code", "list_price", "standard_price", "type"],
            "example_domain": '[["sale_ok", "=", True]]',
        },
        "account.move": {
            "description": "Invoices and bills",
            "key_fields": ["name", "partner_id", "invoice_date", "amount_total", "state", "move_type"],
            "example_domain": '[["move_type", "=", "out_invoice"]]',
        },
        "project.project": {
            "description": "Projects",
            "key_fields": ["name", "partner_id", "date_start", "date", "stage_id"],
            "example_domain": '[["active", "=", True]]',
        },
        "project.task": {
            "description": "Project tasks",
            "key_fields": ["name", "project_id", "user_ids", "date_deadline", "stage_id"],
            "example_domain": '[["active", "=", True]]',
        },
    }
    
    return json.dumps(common_models, indent=2)


@app.resource("odoo://examples/domains")
def get_domain_examples() -> str:
    """Get examples of Odoo domain filters."""
    examples = {
        "basic_filters": {
            "equals": '[["field_name", "=", "value"]]',
            "not_equals": '[["field_name", "!=", "value"]]',
            "contains": '[["field_name", "ilike", "partial_value"]]',
            "in_list": '[["field_name", "in", ["value1", "value2"]]]',
            "greater_than": '[["field_name", ">", 100]]',
            "less_than": '[["field_name", "<", 100]]',
        },
        "logical_operators": {
            "and_implicit": '[["field1", "=", "value1"], ["field2", "=", "value2"]]',
            "and_explicit": '["&", ["field1", "=", "value1"], ["field2", "=", "value2"]]',
            "or": '["|", ["field1", "=", "value1"], ["field2", "=", "value2"]]',
            "not": '["!", ["field1", "=", "value1"]]',
        },
        "date_filters": {
            "today": '[["date_field", "=", "2024-01-15"]]',
            "this_month": '[["date_field", ">=", "2024-01-01"], ["date_field", "<", "2024-02-01"]]',
            "relative": '[["create_date", ">=", "2024-01-01"]]',
        },
        "common_patterns": {
            "active_records": '[["active", "=", True]]',
            "customers_only": '[["customer_rank", ">", 0]]',
            "draft_invoices": '[["state", "=", "draft"], ["move_type", "=", "out_invoice"]]',
            "confirmed_sales": '[["state", "in", ["sale", "done"]]]',
        },
    }
    
    return json.dumps(examples, indent=2)


@app.prompt()
def odoo_query_assistant(
    model: str,
    operation: str = "search",
    requirements: str = "",
) -> str:
    """
    Generate guidance for Odoo operations.
    
    Args:
        model: Odoo model name
        operation: Type of operation (search, create, update, delete)
        requirements: Specific requirements or constraints
    """
    
    if operation == "search":
        return f"""I'll help you search for records in the {model} model.

To search effectively:

1. **Use the search_odoo_records tool** with these parameters:
   - model: "{model}"
   - domain: JSON array of filters (optional)
   - fields: Comma-separated field names (optional)
   - limit: Number of results (default 100)

2. **Common domain examples for {model}:**
   - All records: `[]` (empty domain)
   - Active records: `[["active", "=", True]]`
   - Name contains text: `[["name", "ilike", "search_text"]]`

3. **Useful fields to include:**
   - Basic info: "id,name,display_name"
   - Timestamps: "create_date,write_date"
   - Model-specific fields depend on the model

Requirements: {requirements}

Would you like me to help you build a specific search query?"""

    elif operation == "create":
        return f"""I'll help you create a new record in the {model} model.

To create a record:

1. **Use the create_odoo_record tool** with:
   - model: "{model}"
   - values: JSON object with field values

2. **Required fields:**
   - Check model fields first with get_odoo_model_fields
   - Usually includes "name" for most models
   - May include required relationships

3. **Common field patterns:**
   - Text fields: `"field_name": "value"`
   - Numbers: `"field_name": 123`
   - Booleans: `"field_name": true/false`
   - Relationships: `"field_name": record_id`

Requirements: {requirements}

Let me know what data you want to create and I'll help format it properly."""

    elif operation == "update":
        return f"""I'll help you update records in the {model} model.

To update a record:

1. **First find the record** using search_odoo_records
2. **Use update_odoo_record tool** with:
   - model: "{model}"
   - record_id: ID of the record to update
   - values: JSON object with field changes

3. **Only include fields you want to change**
4. **Use the same format as create operations** for values

Requirements: {requirements}

Do you know the record ID, or do you need to search for it first?"""

    elif operation == "delete":
        return f"""I'll help you delete a record from the {model} model.

⚠️ **Warning: Deletion is permanent!**

To delete a record:

1. **First verify the record** using search_odoo_records
2. **Use delete_odoo_record tool** with:
   - model: "{model}"
   - record_id: ID of the record to delete

3. **Make sure you have the correct record ID**
4. **Consider archiving instead** (set active=False) for most models

Requirements: {requirements}

Are you sure you want to delete this record? Consider searching for it first to confirm."""

    else:
        return f"""I can help you with {model} operations.

Available operations:
- **search**: Find and retrieve records
- **create**: Create new records
- **update**: Modify existing records
- **delete**: Remove records (use with caution)
- **fields**: Get model field information
- **method**: Call custom model methods

Use the odoo_query_assistant prompt with a specific operation for detailed guidance.

Requirements: {requirements}"""


def main() -> None:
    """Main entry point for the MCP server."""
    import sys
    
    # Check if configuration is provided
    try:
        # Try to validate settings
        _ = settings.odoo_url
        _ = settings.odoo_database
        _ = settings.odoo_username
        _ = settings.odoo_password
    except Exception as e:
        print(f"Error: Missing required Odoo configuration: {e}")
        print("\nPlease set the following environment variables:")
        print("- ODOO_URL: Your Odoo server URL")
        print("- ODOO_DATABASE: Your Odoo database name")
        print("- ODOO_USERNAME: Your Odoo username")
        print("- ODOO_PASSWORD: Your Odoo password")
        print("\nOr create a .env file with these settings.")
        sys.exit(1)
    
    # Run the server
    app.run()


if __name__ == "__main__":
    main()