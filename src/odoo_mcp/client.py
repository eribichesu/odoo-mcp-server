"""
Odoo XML-RPC client for async operations.
"""

import asyncio
import json
import logging
import xmlrpc.client
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .config import OdooSettings

if TYPE_CHECKING:
    from .config import Settings

import asyncio
import logging
import xmlrpc.client
from typing import Any, Dict, List, Optional, Union

import requests
from pydantic import HttpUrl

from .config import OdooSettings


logger = logging.getLogger(__name__)


class OdooAuthenticationError(Exception):
    """Raised when authentication with Odoo fails."""


class OdooConnectionError(Exception):
    """Raised when connection to Odoo fails."""


class OdooError(Exception):
    """Base class for Odoo-related errors."""


class OdooClient:
    """
    Asynchronous client for interacting with Odoo via XML-RPC.
    
    This client provides methods for authenticating with Odoo and performing
    CRUD operations on Odoo models.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize the Odoo client.
        
        Args:
            settings: Application settings containing Odoo configuration
        """
        self.url = settings.odoo_url
        self.database = settings.odoo_database
        self.username = settings.odoo_username
        self.password = settings.odoo_password

    async def authenticate(self) -> int:
        """
        Authenticate with Odoo and get user ID.
        
        Returns:
            User ID if authentication successful
            
        Raises:
            OdooAuthenticationError: If authentication fails
            OdooConnectionError: If connection fails
        """
        try:
            # Create common client for authentication
            common_url = f"{self.url}/xmlrpc/2/common"
            self._common = xmlrpc.client.ServerProxy(common_url, timeout=self.timeout)
            
            # Authenticate and get user ID
            self.uid = await self._run_in_executor(
                self._common.authenticate,
                self.database,
                self.username,
                self.password,
                {}
            )
            
            if not self.uid:
                raise OdooAuthenticationError(
                    f"Authentication failed for user '{self.username}' on database '{self.database}'"
                )
            
            # Create models client
            models_url = f"{self.url}/xmlrpc/2/object"
            self._models = xmlrpc.client.ServerProxy(models_url, timeout=self.timeout)
            
            self._authenticated = True
            logger.info(f"Successfully authenticated with Odoo as user {self.uid}")
            
            return self.uid
            
        except xmlrpc.client.Fault as e:
            raise OdooAuthenticationError(f"XML-RPC fault during authentication: {e}")
        except Exception as e:
            raise OdooConnectionError(f"Failed to connect to Odoo: {e}")

    async def check_connection(self) -> Dict[str, Any]:
        """
        Check connection to Odoo and return server info.
        
        Returns:
            Dictionary with server information
        """
        try:
            if not self._common:
                common_url = f"{self.url}/xmlrpc/2/common"
                self._common = xmlrpc.client.ServerProxy(common_url, timeout=self.timeout)
            
            version_info = await self._run_in_executor(self._common.version)
            return {
                "server_version": version_info.get("server_version"),
                "server_serie": version_info.get("server_serie"),
                "protocol_version": version_info.get("protocol_version"),
                "database": self.database,
                "connected": True,
            }
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return {
                "connected": False,
                "error": str(e),
            }

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
        Search for records in an Odoo model.
        
        Args:
            model: Odoo model name (e.g., 'res.partner')
            domain: Search domain filters
            fields: Fields to retrieve
            limit: Maximum number of records to return
            offset: Number of records to skip
            order: Sort order specification
            
        Returns:
            List of record dictionaries
        """
        await self._ensure_authenticated()
        
        if domain is None:
            domain = []
        
        if limit is None:
            limit = self.settings.default_limit
        elif limit > self.settings.max_limit:
            limit = self.settings.max_limit
        
        try:
            # Search for record IDs
            search_kwargs = {
                "offset": offset,
                "limit": limit,
            }
            if order:
                search_kwargs["order"] = order
            
            record_ids = await self._execute_kw(
                model,
                "search",
                [domain],
                search_kwargs,
            )
            
            if not record_ids:
                return []
            
            # Read record data
            records = await self._execute_kw(
                model,
                "read",
                [record_ids],
                {"fields": fields} if fields else {},
            )
            
            return records
            
        except Exception as e:
            raise OdooError(f"Failed to search records in {model}: {e}")

    async def create_record(
        self,
        model: str,
        values: Dict[str, Any],
    ) -> int:
        """
        Create a new record in an Odoo model.
        
        Args:
            model: Odoo model name
            values: Field values for the new record
            
        Returns:
            ID of the created record
        """
        await self._ensure_authenticated()
        
        try:
            record_id = await self._execute_kw(
                model,
                "create",
                [values],
            )
            
            logger.info(f"Created record {record_id} in {model}")
            return record_id
            
        except Exception as e:
            raise OdooError(f"Failed to create record in {model}: {e}")

    async def update_record(
        self,
        model: str,
        record_id: int,
        values: Dict[str, Any],
    ) -> bool:
        """
        Update an existing record in an Odoo model.
        
        Args:
            model: Odoo model name
            record_id: ID of the record to update
            values: Field values to update
            
        Returns:
            True if update was successful
        """
        await self._ensure_authenticated()
        
        try:
            result = await self._execute_kw(
                model,
                "write",
                [[record_id], values],
            )
            
            logger.info(f"Updated record {record_id} in {model}")
            return result
            
        except Exception as e:
            raise OdooError(f"Failed to update record {record_id} in {model}: {e}")

    async def delete_record(
        self,
        model: str,
        record_id: int,
    ) -> bool:
        """
        Delete a record from an Odoo model.
        
        Args:
            model: Odoo model name
            record_id: ID of the record to delete
            
        Returns:
            True if deletion was successful
        """
        await self._ensure_authenticated()
        
        try:
            result = await self._execute_kw(
                model,
                "unlink",
                [[record_id]],
            )
            
            logger.info(f"Deleted record {record_id} from {model}")
            return result
            
        except Exception as e:
            raise OdooError(f"Failed to delete record {record_id} from {model}: {e}")

    async def get_model_fields(self, model: str) -> Dict[str, Any]:
        """
        Get field definitions for an Odoo model.
        
        Args:
            model: Odoo model name
            
        Returns:
            Dictionary of field definitions
        """
        await self._ensure_authenticated()
        
        try:
            fields = await self._execute_kw(
                model,
                "fields_get",
                [],
            )
            
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
        Execute a method on an Odoo model with retry logic.
        
        Args:
            model: Odoo model name
            method: Method name
            args: Method arguments
            kwargs: Method keyword arguments
            
        Returns:
            Method result
        """
        if kwargs is None:
            kwargs = {}
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._run_in_executor(
                    self._models.execute_kw,
                    self.database,
                    self.uid,
                    self.password,
                    model,
                    method,
                    args,
                    kwargs,
                )
                return result
                
            except Exception as e:
                if attempt == self.max_retries:
                    raise e
                
                logger.warning(
                    f"Attempt {attempt + 1} failed for {model}.{method}: {e}. "
                    f"Retrying in {self.retry_delay} seconds..."
                )
                await asyncio.sleep(self.retry_delay)

    async def _ensure_authenticated(self) -> None:
        """Ensure the client is authenticated."""
        if not self._authenticated or not self.uid:
            await self.authenticate()

    async def _run_in_executor(self, func, *args) -> Any:
        """Run a blocking function in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)