"""
Async Odoo client.

Exposes CRUD, search and metadata operations on top of a pluggable transport
(XML-RPC or JSON-2 — see ``transport.py``). The client is transport-agnostic:
it always speaks the ``execute_kw(model, method, args, kwargs)`` convention and
the transport translates it to the wire format.
"""

import logging
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from .errors import (
    OdooAuthenticationError,
    OdooConnectionError,
    OdooError,
    OdooRequestError,
)
from .transport import create_transport

if TYPE_CHECKING:
    from .config import Settings


logger = logging.getLogger(__name__)


def _single_id(result: Any) -> Any:
    """Normalize a create/copy result to a single id.

    XML-RPC ``create``/``copy`` return a bare int, but the JSON-2 API uses
    create-multi semantics and returns a list of ids (e.g. ``[224]``). Callers
    of ``create_record``/``copy_record`` expect a single id, so unwrap a
    one-element list.
    """
    if isinstance(result, list):
        return result[0] if result else None
    return result


# Re-exported for backwards compatibility (these used to live in this module).
__all__ = [
    "OdooClient",
    "OdooError",
    "OdooAuthenticationError",
    "OdooConnectionError",
    "OdooRequestError",
]


class OdooClient:
    """
    Asynchronous client for interacting with Odoo.

    Connection, authentication and retries are delegated to a transport selected
    by configuration (``ODOO_TRANSPORT``): JSON-2 for Odoo 19+, XML-RPC for
    older instances.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize the Odoo client.

        Args:
            settings: Application settings containing Odoo configuration
        """
        self.database = settings.odoo_database
        self.default_limit = settings.default_limit
        self.max_limit = settings.max_limit

        self._transport = create_transport(settings)

    @property
    def transport_name(self) -> str:
        """Name of the active transport ('json2' or 'xmlrpc')."""
        return self._transport.name

    async def check_connection(self) -> Dict[str, Any]:
        """
        Check connection to Odoo and return server info.

        Returns:
            Dictionary with server information and the active transport.
        """
        return await self._transport.check_connection()

    async def search_records(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for records in an Odoo model (two round-trips: search then read).
        Prefer search_read() for better performance.
        """
        await self._ensure_authenticated()

        if domain is None:
            domain = []

        if limit is None:
            limit = self.default_limit
        elif limit > self.max_limit:
            limit = self.max_limit

        try:
            search_kwargs: Dict[str, Any] = {"offset": offset, "limit": limit}
            if order:
                search_kwargs["order"] = order

            record_ids = await self._execute_kw(model, "search", [domain], search_kwargs)

            if not record_ids:
                return []

            records = await self._execute_kw(
                model, "read", [record_ids], {"fields": fields} if fields else {}
            )
            return records

        except Exception as e:
            raise OdooError(f"Failed to search records in {model}: {e}")

    async def search_read(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search and read records in a single RPC call (more efficient than search + read).

        Returns:
            List of record dictionaries
        """
        await self._ensure_authenticated()

        if domain is None:
            domain = []

        if limit is None:
            limit = self.default_limit
        elif limit > self.max_limit:
            limit = self.max_limit

        try:
            kwargs: Dict[str, Any] = {"offset": offset, "limit": limit}
            if fields:
                kwargs["fields"] = fields
            if order:
                kwargs["order"] = order

            records = await self._execute_kw(model, "search_read", [domain], kwargs)
            return records

        except Exception as e:
            raise OdooError(f"Failed to search_read records in {model}: {e}")

    async def search_count(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
    ) -> int:
        """
        Count records matching a domain without fetching data.

        Returns:
            Integer count of matching records
        """
        await self._ensure_authenticated()

        if domain is None:
            domain = []

        try:
            count = await self._execute_kw(model, "search_count", [domain])
            return count

        except Exception as e:
            raise OdooError(f"Failed to count records in {model}: {e}")

    async def read_group(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        groupby: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        orderby: Optional[str] = None,
        lazy: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Group records and aggregate field values (SQL GROUP BY equivalent).

        Args:
            fields: Fields to aggregate, e.g. ['amount_total:sum', 'partner_id']
            groupby: Fields to group by, supports date granularity: 'date:month'
            lazy: If True, only groups by first field; remaining go to __context

        Returns:
            List of group dicts, each with __count and aggregated values
        """
        await self._ensure_authenticated()

        if domain is None:
            domain = []
        if fields is None:
            fields = []
        if groupby is None:
            groupby = []

        try:
            kwargs: Dict[str, Any] = {
                "fields": fields,
                "groupby": groupby,
                "offset": offset,
                "lazy": lazy,
            }
            if limit is not None:
                kwargs["limit"] = limit
            if orderby:
                kwargs["orderby"] = orderby

            result = await self._execute_kw(model, "read_group", [domain], kwargs)
            return result

        except Exception as e:
            raise OdooError(f"Failed to read_group on {model}: {e}")

    async def get_default_values(
        self,
        model: str,
        fields: List[str],
    ) -> Dict[str, Any]:
        """
        Get default values Odoo would pre-fill for a new record.

        Returns:
            Dict of {field_name: default_value}
        """
        await self._ensure_authenticated()

        try:
            defaults = await self._execute_kw(model, "default_get", [fields])
            return defaults

        except Exception as e:
            raise OdooError(f"Failed to get default values for {model}: {e}")

    async def name_search(
        self,
        model: str,
        name: str = "",
        domain: Optional[List[Any]] = None,
        operator: str = "ilike",
        limit: int = 10,
    ) -> List[List[Any]]:
        """
        Search records by display name — used for autocomplete / many2one lookups.

        Returns:
            List of [id, display_name] pairs
        """
        await self._ensure_authenticated()

        if domain is None:
            domain = []

        try:
            result = await self._execute_kw(
                model,
                "name_search",
                [],
                {"name": name, "domain": domain, "operator": operator, "limit": limit},
            )
            return result

        except Exception as e:
            raise OdooError(f"Failed to name_search on {model}: {e}")

    async def copy_record(
        self,
        model: str,
        record_id: int,
        default: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Duplicate a record, optionally overriding field values.

        Returns:
            ID of the new (copied) record
        """
        await self._ensure_authenticated()

        try:
            kwargs: Dict[str, Any] = {}
            if default:
                kwargs["default"] = default

            new_id = await self._execute_kw(model, "copy", [record_id], kwargs)
            new_id = _single_id(new_id)
            logger.info(f"Copied record {record_id} in {model} -> new id {new_id}")
            return new_id

        except Exception as e:
            raise OdooError(f"Failed to copy record {record_id} in {model}: {e}")

    async def get_external_id(
        self,
        model: str,
        record_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Get XML/external IDs for records via ir.model.data.
        Works around the XML-RPC integer-key limitation in Odoo 19+.

        Returns:
            List of dicts with res_id, module, name (full external ID = module.name)
        """
        await self._ensure_authenticated()

        try:
            result = await self._execute_kw(
                "ir.model.data",
                "search_read",
                [[["model", "=", model], ["res_id", "in", record_ids]]],
                {"fields": ["res_id", "module", "name"]},
            )
            return result

        except Exception as e:
            raise OdooError(f"Failed to get external IDs for {model}: {e}")

    async def export_data(
        self,
        model: str,
        record_ids: List[int],
        fields: List[str],
    ) -> Dict[str, Any]:
        """
        Export records in CSV-compatible format with support for dotted paths
        (e.g. 'country_id/name' for related fields).

        Returns:
            Dict with 'datas' key containing a list of rows (each a list of values)
        """
        await self._ensure_authenticated()

        try:
            result = await self._execute_kw(
                model, "export_data", [record_ids, fields]
            )
            return result

        except Exception as e:
            raise OdooError(f"Failed to export data from {model}: {e}")

    async def load_data(
        self,
        model: str,
        fields: List[str],
        data: List[List[Any]],
    ) -> Dict[str, Any]:
        """
        Import/bulk-load records. Equivalent to Odoo UI import.

        Args:
            fields: Column headers matching field names (supports 'field/subfield')
            data: List of rows, each a list of string values

        Returns:
            Dict with 'ids' (created/updated IDs) and 'messages' (warnings/errors)
        """
        await self._ensure_authenticated()

        try:
            result = await self._execute_kw(model, "load", [fields, data])
            return result

        except Exception as e:
            raise OdooError(f"Failed to load data into {model}: {e}")

    async def list_models(
        self,
        name_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all installed Odoo models via ir.model.

        Args:
            name_filter: Optional substring to filter by technical model name (e.g. 'sale')

        Returns:
            List of dicts with model name, label, and state
        """
        await self._ensure_authenticated()

        domain: List[Any] = []
        if name_filter:
            domain = [["model", "ilike", name_filter]]

        try:
            result = await self._execute_kw(
                "ir.model",
                "search_read",
                [domain],
                {
                    "fields": ["name", "model", "state", "info"],
                    "order": "model asc",
                },
            )
            return result

        except Exception as e:
            raise OdooError(f"Failed to list models: {e}")

    async def create_record(
        self,
        model: str,
        values: Dict[str, Any],
    ) -> int:
        """
        Create a new record in an Odoo model.

        Returns:
            ID of the created record
        """
        await self._ensure_authenticated()

        try:
            record_id = await self._execute_kw(model, "create", [values])
            record_id = _single_id(record_id)
            logger.info(f"Created record {record_id} in {model}")
            return record_id

        except Exception as e:
            raise OdooError(f"Failed to create record in {model}: {e}")

    async def update_record(
        self,
        model: str,
        record_ids: Union[int, List[int]],
        values: Dict[str, Any],
    ) -> bool:
        """
        Update one or more records in an Odoo model.

        Args:
            record_ids: Single ID or list of IDs to update

        Returns:
            True if update was successful
        """
        await self._ensure_authenticated()

        ids = [record_ids] if isinstance(record_ids, int) else record_ids

        try:
            result = await self._execute_kw(model, "write", [ids, values])
            logger.info(f"Updated records {ids} in {model}")
            return result

        except Exception as e:
            raise OdooError(f"Failed to update records {ids} in {model}: {e}")

    async def delete_record(
        self,
        model: str,
        record_ids: Union[int, List[int]],
    ) -> bool:
        """
        Delete one or more records from an Odoo model.

        Args:
            record_ids: Single ID or list of IDs to delete

        Returns:
            True if deletion was successful
        """
        await self._ensure_authenticated()

        ids = [record_ids] if isinstance(record_ids, int) else record_ids

        try:
            result = await self._execute_kw(model, "unlink", [ids])
            logger.info(f"Deleted records {ids} from {model}")
            return result

        except Exception as e:
            raise OdooError(f"Failed to delete records {ids} from {model}: {e}")

    async def get_model_fields(
        self,
        model: str,
        attributes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get field definitions for an Odoo model.

        Args:
            attributes: Optional list of attributes to return per field, e.g.
                ['string', 'type', 'required', 'readonly', 'relation'].
                Defaults to all attributes if omitted.

        Returns:
            Dictionary of field definitions keyed by field name
        """
        await self._ensure_authenticated()

        try:
            kwargs: Dict[str, Any] = {}
            if attributes:
                kwargs["attributes"] = attributes

            fields = await self._execute_kw(model, "fields_get", [], kwargs)
            return fields

        except Exception as e:
            raise OdooError(f"Failed to get fields for model {model}: {e}")

    async def call_method(
        self,
        model: str,
        method: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Call a custom method on an Odoo model.
        
        Args:
            model: Odoo model name
            method: Method name to call
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Method result
        """
        await self._ensure_authenticated()
        
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        
        try:
            result = await self._execute_kw(model, method, args, kwargs)
            return result
            
        except Exception as e:
            raise OdooError(f"Failed to call method {method} on {model}: {e}")

    async def _execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a method on an Odoo model via the active transport.

        Retries, authentication and the on-the-wire format are handled by the
        transport (see ``transport.py``).

        Args:
            model: Odoo model name
            method: Method name
            args: Method arguments
            kwargs: Method keyword arguments

        Returns:
            Method result
        """
        return await self._transport.execute_kw(model, method, args, kwargs or {})

    async def _ensure_authenticated(self) -> None:
        """Authentication is performed lazily by the transport on first use.

        Kept as a no-op so the operation methods can call it uniformly.
        """
        return None