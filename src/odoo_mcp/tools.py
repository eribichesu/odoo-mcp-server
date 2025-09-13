"""
Tool definitions for Odoo MCP operations.

This module contains individual tool functions that can be used by the MCP server
to perform various Odoo operations.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .client import OdooClient, OdooError


logger = logging.getLogger(__name__)


async def search_records_tool(
    client: OdooClient,
    model: str,
    domain: Optional[List[Any]] = None,
    fields: Optional[List[str]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for records in an Odoo model.
    
    Args:
        client: Authenticated Odoo client
        model: Odoo model name
        domain: Search domain filters
        fields: Fields to retrieve
        limit: Maximum number of records
        offset: Records to skip
        order: Sort order
        
    Returns:
        Dictionary with search results
    """
    try:
        records = await client.search_records(
            model=model,
            domain=domain,
            fields=fields,
            limit=limit,
            offset=offset,
            order=order,
        )
        
        return {
            "success": True,
            "model": model,
            "count": len(records),
            "records": records,
        }
        
    except OdooError as e:
        logger.error(f"Odoo error in search_records_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "OdooError",
        }
    except Exception as e:
        logger.error(f"Unexpected error in search_records_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "UnexpectedError",
        }


async def create_record_tool(
    client: OdooClient,
    model: str,
    values: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new record in an Odoo model.
    
    Args:
        client: Authenticated Odoo client
        model: Odoo model name
        values: Field values for new record
        
    Returns:
        Dictionary with creation result
    """
    try:
        record_id = await client.create_record(model, values)
        
        return {
            "success": True,
            "model": model,
            "record_id": record_id,
            "values": values,
        }
        
    except OdooError as e:
        logger.error(f"Odoo error in create_record_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "OdooError",
        }
    except Exception as e:
        logger.error(f"Unexpected error in create_record_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "UnexpectedError",
        }


async def update_record_tool(
    client: OdooClient,
    model: str,
    record_id: int,
    values: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing record in an Odoo model.
    
    Args:
        client: Authenticated Odoo client
        model: Odoo model name
        record_id: ID of record to update
        values: Field values to update
        
    Returns:
        Dictionary with update result
    """
    try:
        success = await client.update_record(model, record_id, values)
        
        return {
            "success": success,
            "model": model,
            "record_id": record_id,
            "values": values,
        }
        
    except OdooError as e:
        logger.error(f"Odoo error in update_record_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "OdooError",
        }
    except Exception as e:
        logger.error(f"Unexpected error in update_record_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "UnexpectedError",
        }


async def delete_record_tool(
    client: OdooClient,
    model: str,
    record_id: int,
) -> Dict[str, Any]:
    """
    Delete a record from an Odoo model.
    
    Args:
        client: Authenticated Odoo client
        model: Odoo model name
        record_id: ID of record to delete
        
    Returns:
        Dictionary with deletion result
    """
    try:
        success = await client.delete_record(model, record_id)
        
        return {
            "success": success,
            "model": model,
            "record_id": record_id,
        }
        
    except OdooError as e:
        logger.error(f"Odoo error in delete_record_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "OdooError",
        }
    except Exception as e:
        logger.error(f"Unexpected error in delete_record_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "UnexpectedError",
        }


async def get_model_fields_tool(
    client: OdooClient,
    model: str,
) -> Dict[str, Any]:
    """
    Get field definitions for an Odoo model.
    
    Args:
        client: Authenticated Odoo client
        model: Odoo model name
        
    Returns:
        Dictionary with field definitions
    """
    try:
        fields = await client.get_model_fields(model)
        
        return {
            "success": True,
            "model": model,
            "fields": fields,
        }
        
    except OdooError as e:
        logger.error(f"Odoo error in get_model_fields_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "OdooError",
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_model_fields_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "UnexpectedError",
        }


async def call_method_tool(
    client: OdooClient,
    model: str,
    method: str,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call a custom method on an Odoo model.
    
    Args:
        client: Authenticated Odoo client
        model: Odoo model name
        method: Method name to call
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Dictionary with method result
    """
    try:
        result = await client.call_method(model, method, args, kwargs)
        
        return {
            "success": True,
            "model": model,
            "method": method,
            "result": result,
        }
        
    except OdooError as e:
        logger.error(f"Odoo error in call_method_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "OdooError",
        }
    except Exception as e:
        logger.error(f"Unexpected error in call_method_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "UnexpectedError",
        }