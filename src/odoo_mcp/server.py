"""
Main MCP server implementation for Odoo integration.
"""

import asyncio
import json
import logging
import sys
import os
from typing import Any, Dict, List, Optional, Sequence, Union

# Add the parent directory to sys.path to handle relative imports
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

try:
    from .client import OdooClient, OdooError
    from .config import get_settings
except ImportError:
    # Fallback for direct execution
    from odoo_mcp.client import OdooClient, OdooError
    from odoo_mcp.config import get_settings


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


@app.tool(
    annotations=ToolAnnotations(
        title="Check Odoo Connection",
        readOnlyHint=True,
        openWorldHint=True,
    )
)
async def check_odoo_connection() -> Dict[str, Any]:
    """
    Check the connection to the Odoo server and return status information,
    including which transport is active ('json2' for Odoo 19+, or 'xmlrpc') and
    the server version.

    Returns:
        Connection status, active transport, and server information
    """
    try:
        client = await get_odoo_client()
        info = await client.check_connection()
        info.setdefault("mcp_server_version", settings.server_version)
        return info

    except Exception as e:
        logger.error(f"Connection check failed: {e}")
        return {"connected": False, "error": str(e)}


def _parse_domain(domain: Optional[Union[str, List[Any]]]) -> Optional[List[Any]]:
    """Parse domain from JSON string or list. Returns None on invalid input."""
    if not domain:
        return None
    if isinstance(domain, list):
        return domain
    if isinstance(domain, str):
        return json.loads(domain)
    raise ValueError(f"Domain must be a JSON string or list, got {type(domain).__name__}")


def _parse_json(value: Optional[Union[str, dict, list]], name: str = "value") -> Any:
    """Parse a JSON string or pass through dict/list as-is."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise ValueError(f"{name} must be a JSON string or dict/list, got {type(value).__name__}")


@app.tool(
    annotations=ToolAnnotations(title="Search Odoo Records", readOnlyHint=True)
)
async def search_odoo_records(
    model: str,
    domain: Optional[Union[str, List[Any]]] = None,
    fields: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for records in an Odoo model and return matching records with field data.
    Uses a single search_read RPC call for efficiency.
    Prefer this over calling search then read separately.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'sale.order')
        domain: Search filter as JSON list of triples, e.g. '[["customer_rank",">",0]]'. Use '[]' or omit for all records.
        fields: Comma-separated field names to return, e.g. 'name,email,phone'. Omit for all fields.
        limit: Max records to return (default 100, max 1000)
        offset: Records to skip for pagination (default 0)
        order: Sort order, e.g. 'name ASC' or 'create_date DESC'

    Returns:
        JSON with 'model', 'count', and 'records' list
    """
    try:
        client = await get_odoo_client()
        parsed_domain = _parse_domain(domain)
        parsed_fields = [f.strip() for f in fields.split(",")] if fields else None

        records = await client.search_read(
            model=model,
            domain=parsed_domain,
            fields=parsed_fields,
            limit=limit,
            offset=offset,
            order=order,
        )

        return {"model": model, "count": len(records), "records": records}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(
        title="Create Odoo Record",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )
)
async def create_odoo_record(
    model: str,
    values: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a new record in an Odoo model.
    Use get_odoo_model_fields first to know required fields and their types.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'sale.order')
        values: Field values as JSON string or dict, e.g. '{"name": "ACME", "email": "info@acme.com"}'
                For many2one fields use the related record's ID (integer).
                For many2many/one2many use Odoo command syntax: [[6, 0, [id1, id2]]] to replace.

    Returns:
        JSON with 'model', 'record_id' (new record's ID), and 'success'
    """
    try:
        client = await get_odoo_client()
        parsed_values = _parse_json(values, "values")

        record_id = await client.create_record(model, parsed_values)

        return {"model": model, "record_id": record_id, "success": True}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(
        title="Update Odoo Record",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
    )
)
async def update_odoo_record(
    model: str,
    record_ids: Union[int, str, List[Any]],
    values: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Update one or more existing records in an Odoo model.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'sale.order')
        record_ids: Single record ID (int) or list of IDs to update, e.g. 42 or [42, 43]
        values: Field values to update as JSON string or dict, e.g. '{"name": "New Name"}' or {"active": false}

    Returns:
        JSON with 'success' boolean, model name, and updated IDs
    """
    try:
        client = await get_odoo_client()
        parsed_ids = _parse_json(record_ids if isinstance(record_ids, str) else record_ids, "record_ids")
        parsed_values = _parse_json(values, "values")

        success = await client.update_record(model, parsed_ids, parsed_values)

        return {"model": model, "record_ids": parsed_ids, "values": parsed_values, "success": success}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(
        title="Delete Odoo Record",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
    )
)
async def delete_odoo_record(
    model: str,
    record_ids: Union[int, str, List[Any]],
) -> Dict[str, Any]:
    """
    Delete one or more records from an Odoo model. This is permanent and cannot be undone.
    Consider archiving instead (update active=false) when supported by the model.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'sale.order')
        record_ids: Single record ID (int) or list of IDs to delete, e.g. 42 or [42, 43]

    Returns:
        JSON with 'success' boolean, model name, and deleted IDs
    """
    try:
        client = await get_odoo_client()
        parsed_ids = _parse_json(record_ids if isinstance(record_ids, str) else record_ids, "record_ids")

        success = await client.delete_record(model, parsed_ids)

        return {"model": model, "record_ids": parsed_ids, "success": success}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Get Odoo Model Fields", readOnlyHint=True)
)
async def get_odoo_model_fields(
    model: str,
    attributes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get field definitions and metadata for an Odoo model.
    Use this before create/update to understand required fields, types, and relations.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'sale.order')
        attributes: Comma-separated field attributes to return, e.g. 'string,type,required,readonly,relation'.
                    Omit to get all attributes (verbose). Recommended: 'string,type,required,relation'

    Returns:
        JSON with 'model' and 'fields' dict keyed by field name
    """
    try:
        client = await get_odoo_client()
        parsed_attributes = [a.strip() for a in attributes.split(",")] if attributes else None

        fields = await client.get_model_fields(model, attributes=parsed_attributes)

        return {"model": model, "fields": fields}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(
        title="Call Odoo Method",
        readOnlyHint=False,
        destructiveHint=True,
        openWorldHint=True,
    )
)
async def call_odoo_method(
    model: str,
    method: str,
    args: Optional[Union[str, List[Any]]] = None,
    kwargs: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Call any public method on an Odoo model via execute_kw.
    Use this for business logic methods not covered by other tools, such as:
    action_confirm (confirm sale/PO), action_post (post journal entry),
    action_invoice_open, button_validate (validate picking), send_mail, etc.

    Args:
        model: Odoo model technical name (e.g., 'sale.order', 'account.move')
        method: Method name to call (e.g., 'action_confirm', 'action_post', 'button_validate')
        args: Positional arguments as JSON list, e.g. '[[42, 43]]' (first arg is usually a list of IDs)
        kwargs: Keyword arguments as JSON dict, e.g. '{"context": {"lang": "en_US"}}'

    Returns:
        JSON with 'model', 'method', and 'result' (method return value)
    """
    try:
        client = await get_odoo_client()
        parsed_args = _parse_json(args, "args") or []
        parsed_kwargs = _parse_json(kwargs, "kwargs") or {}

        result = await client.call_method(model, method, parsed_args, parsed_kwargs)

        return {"model": model, "method": method, "result": result}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Count Odoo Records", readOnlyHint=True)
)
async def count_odoo_records(
    model: str,
    domain: Optional[Union[str, List[Any]]] = None,
) -> Dict[str, Any]:
    """
    Count records matching a domain filter without fetching any data.
    Use this instead of search_odoo_records when you only need the count.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'sale.order')
        domain: Search filter as JSON list, e.g. '[["state","=","sale"]]'. Use '[]' or omit for all records.

    Returns:
        JSON with 'model', 'domain', and 'count' (integer)
    """
    try:
        client = await get_odoo_client()
        parsed_domain = _parse_domain(domain)

        count = await client.search_count(model, parsed_domain)

        return {"model": model, "domain": parsed_domain, "count": count}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Group Odoo Records", readOnlyHint=True)
)
async def group_odoo_records(
    model: str,
    groupby: str,
    fields: Optional[str] = None,
    domain: Optional[Union[str, List[Any]]] = None,
    limit: Optional[int] = None,
    orderby: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Group and aggregate records — equivalent to SQL GROUP BY with SUM/COUNT.
    Use for reporting, dashboards, and analytics. Each result group includes __count.
    On Odoo 19+ this uses formatted_read_group (read_group is deprecated); groups
    carry an __extra_domain you can feed straight back into a search.

    Args:
        model: Odoo model technical name (e.g., 'sale.order', 'account.move')
        groupby: Comma-separated fields to group by. Supports date granularity: 'date_order:month', 'create_date:year'
        fields: Comma-separated aggregate specs, e.g. 'amount_total:sum,amount_total:avg'.
                Must be 'field:agg' form; plain group-field names are ignored. Omit for just counts.
        domain: Filter as JSON list, e.g. '[["state","=","sale"]]'. Use '[]' or omit for all records.
        limit: Max number of groups to return
        orderby: Sort order for groups, e.g. 'amount_total:sum desc' or '__count desc'

    Returns:
        JSON with 'model' and 'groups' list. Each group has __count, grouped field value, and aggregated values.
    """
    try:
        client = await get_odoo_client()
        parsed_domain = _parse_domain(domain)
        parsed_groupby = [g.strip() for g in groupby.split(",")]
        parsed_fields = [f.strip() for f in fields.split(",")] if fields else parsed_groupby

        groups = await client.read_group(
            model=model,
            domain=parsed_domain,
            fields=parsed_fields,
            groupby=parsed_groupby,
            limit=limit,
            orderby=orderby,
        )

        return {"model": model, "groups": groups}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Get Odoo Default Values", readOnlyHint=True)
)
async def get_odoo_default_values(
    model: str,
    fields: str,
) -> Dict[str, Any]:
    """
    Get the default values Odoo would pre-fill when creating a new record.
    Call this before create_odoo_record to know what fields have defaults.

    Args:
        model: Odoo model technical name (e.g., 'sale.order', 'res.partner')
        fields: Comma-separated field names to get defaults for, e.g. 'state,pricelist_id,company_id'

    Returns:
        JSON with 'model' and 'defaults' dict of {field_name: default_value}
    """
    try:
        client = await get_odoo_client()
        parsed_fields = [f.strip() for f in fields.split(",")]

        defaults = await client.get_default_values(model, parsed_fields)

        return {"model": model, "defaults": defaults}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Name Search Odoo", readOnlyHint=True)
)
async def name_search_odoo(
    model: str,
    name: str = "",
    domain: Optional[Union[str, List[Any]]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search records by display name — used for autocomplete and many2one field lookups.
    Returns [id, display_name] pairs. Use this to find a record's ID from its name.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'product.product')
        name: Name substring to search for (case-insensitive). Use '' to get any records.
        domain: Additional filter as JSON list, e.g. '[["is_company","=",true]]'
        limit: Max results to return (default 10)

    Returns:
        JSON with 'model', 'name', and 'results' list of [[id, display_name], ...]
    """
    try:
        client = await get_odoo_client()
        parsed_domain = _parse_domain(domain)

        results = await client.name_search(
            model=model,
            name=name,
            domain=parsed_domain,
            limit=limit,
        )

        return {"model": model, "name": name, "results": results}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(
        title="Copy Odoo Record",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )
)
async def copy_odoo_record(
    model: str,
    record_id: int,
    default: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Duplicate an existing record, optionally overriding field values in the copy.
    Fields marked copy=False in the model (like unique sequences) are not copied.

    Args:
        model: Odoo model technical name (e.g., 'sale.order', 'product.template')
        record_id: ID of the record to duplicate
        default: Optional field overrides for the new copy as JSON dict, e.g. '{"name": "Copy of SO-001"}'

    Returns:
        JSON with 'model', 'source_id', and 'new_record_id'
    """
    try:
        client = await get_odoo_client()
        parsed_default = _parse_json(default, "default") if default else None

        new_id = await client.copy_record(model, record_id, parsed_default)

        return {"model": model, "source_id": record_id, "new_record_id": new_id}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Get Odoo External ID", readOnlyHint=True)
)
async def get_odoo_external_id(
    model: str,
    record_ids: Union[str, List[Any]],
) -> Dict[str, Any]:
    """
    Get the XML/external IDs for records (e.g. 'base.res_partner_address_1').
    External IDs are used in data files, migrations, and cross-database references.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'res.country')
        record_ids: List of record IDs as JSON array, e.g. '[1, 2, 3]'

    Returns:
        JSON with 'model' and 'external_ids' dict of {record_id: 'module.xml_id'}
    """
    try:
        client = await get_odoo_client()
        parsed_ids = _parse_json(record_ids, "record_ids")

        result = await client.get_external_id(model, parsed_ids)

        return {"model": model, "external_ids": result}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="Export Odoo Data", readOnlyHint=True)
)
async def export_odoo_data(
    model: str,
    record_ids: Union[str, List[Any]],
    fields: str,
) -> Dict[str, Any]:
    """
    Export records in CSV-compatible format. Supports dotted paths for related fields
    (e.g. 'country_id/name' to get the country name instead of the ID).
    Use this to extract data for reporting or migration.

    Args:
        model: Odoo model technical name (e.g., 'res.partner', 'account.move')
        record_ids: List of record IDs as JSON array, e.g. '[1, 2, 3]'
        fields: Comma-separated field paths, e.g. 'name,email,country_id/name,parent_id/name'

    Returns:
        JSON with 'model', 'fields', and 'rows' (list of value lists, one per record)
    """
    try:
        client = await get_odoo_client()
        parsed_ids = _parse_json(record_ids, "record_ids")
        parsed_fields = [f.strip() for f in fields.split(",")]

        result = await client.export_data(model, parsed_ids, parsed_fields)

        return {"model": model, "fields": parsed_fields, "rows": result.get("datas", [])}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@app.tool(
    annotations=ToolAnnotations(title="List Odoo Models", readOnlyHint=True)
)
async def list_odoo_models(
    filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all installed Odoo models available in this instance.
    Use this to discover which models exist before calling other tools.
    Returns technical name (e.g. 'sale.order'), human label, and state (base/manual).

    Args:
        filter: Optional substring to filter by technical model name, e.g. 'sale', 'account', 'hr'

    Returns:
        JSON with 'count' and 'models' list of {name, model, state} dicts
    """
    try:
        client = await get_odoo_client()

        models = await client.list_models(name_filter=filter)

        return {"count": len(models), "models": models}

    except OdooError as e:
        return {"error": f"Odoo error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


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