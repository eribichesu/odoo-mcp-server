"""
Transport layer for talking to Odoo's external API.

Two transports are provided behind a common interface:

* ``XmlRpcTransport`` — the legacy ``/xmlrpc/2`` endpoints. Deprecated in
  Odoo 19 (removed on Odoo Online in 19.1 and on-prem in 20) but still the only
  option for Odoo <= 18.
* ``Json2Transport`` — the modern ``/json/2`` endpoint introduced in Odoo 19.
  Uses API-key bearer auth, named parameters, and real HTTP status codes.

Both expose the same ``execute_kw(model, method, args, kwargs)`` surface so the
``OdooClient`` above does not care which one is in use.
"""

import asyncio
import logging
import xmlrpc.client
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests

from .errors import (
    OdooAuthenticationError,
    OdooConnectionError,
    OdooRequestError,
)

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)


class OdooTransport:
    """Common base for the concrete transports."""

    name: str = "base"

    def __init__(self, settings: "Settings") -> None:
        self.url = str(settings.odoo_url).rstrip("/")
        self.database = settings.odoo_database
        self.timeout = settings.odoo_timeout
        self.max_retries = settings.odoo_max_retries
        self.retry_delay = settings.odoo_retry_delay

    async def _run_in_executor(self, func, *args) -> Any:
        """Run a blocking function in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        raise NotImplementedError

    async def version(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def check_connection(self) -> Dict[str, Any]:
        """Best-effort connectivity + version probe, shared by both transports."""
        try:
            info = await self.version()
            return {
                "connected": True,
                "transport": self.name,
                "database": self.database,
                **info,
            }
        except Exception as e:  # noqa: BLE001 - surfaced to the caller as JSON
            logger.error(f"[{self.name}] connection check failed: {e}")
            return {
                "connected": False,
                "transport": self.name,
                "database": self.database,
                "error": str(e),
            }


class XmlRpcTransport(OdooTransport):
    """Legacy XML-RPC transport (``/xmlrpc/2``)."""

    name = "xmlrpc"

    def __init__(self, settings: "Settings") -> None:
        super().__init__(settings)
        self.username = settings.odoo_username
        # An API key can be used in place of the password and is required when
        # two-factor authentication is enabled on the account.
        self.secret = settings.odoo_api_key or settings.odoo_password
        self._common: Optional[xmlrpc.client.ServerProxy] = None
        self._models: Optional[xmlrpc.client.ServerProxy] = None
        self.uid: Optional[int] = None

    def _server_proxy(self, path: str) -> xmlrpc.client.ServerProxy:
        endpoint = f"{self.url}{path}"
        try:
            return xmlrpc.client.ServerProxy(endpoint, timeout=self.timeout)
        except TypeError:
            # Older Python versions without the timeout kwarg.
            return xmlrpc.client.ServerProxy(endpoint)

    async def _ensure_auth(self) -> None:
        if self.uid and self._models is not None:
            return
        self._common = self._server_proxy("/xmlrpc/2/common")
        try:
            self.uid = await self._run_in_executor(
                self._common.authenticate,
                self.database,
                self.username,
                self.secret,
                {},
            )
        except xmlrpc.client.Fault as e:
            raise OdooAuthenticationError(f"XML-RPC authentication fault: {e}") from e
        except Exception as e:  # noqa: BLE001
            raise OdooConnectionError(f"Failed to reach Odoo: {e}") from e

        if not self.uid:
            raise OdooAuthenticationError(
                f"Authentication failed for user '{self.username}' on database "
                f"'{self.database}'. If 2FA is enabled, use an API key."
            )
        self._models = self._server_proxy("/xmlrpc/2/object")
        logger.info(f"Authenticated with Odoo via XML-RPC as uid {self.uid}")

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        await self._ensure_auth()
        kwargs = kwargs or {}

        for attempt in range(self.max_retries + 1):
            try:
                return await self._run_in_executor(
                    self._models.execute_kw,
                    self.database,
                    self.uid,
                    self.secret,
                    model,
                    method,
                    args,
                    kwargs,
                )
            except xmlrpc.client.Fault as e:
                # Server-side business error — retrying cannot help.
                raise OdooRequestError(f"{model}.{method} failed: {e.faultString}") from e
            except Exception as e:  # noqa: BLE001 - transport-level, retry
                if attempt == self.max_retries:
                    raise OdooConnectionError(
                        f"{model}.{method} failed after {attempt + 1} attempts: {e}"
                    ) from e
                logger.warning(
                    f"[xmlrpc] attempt {attempt + 1} for {model}.{method} failed: {e}. "
                    f"Retrying in {self.retry_delay}s..."
                )
                await asyncio.sleep(self.retry_delay)

    async def version(self) -> Dict[str, Any]:
        common = self._server_proxy("/xmlrpc/2/common")
        info = await self._run_in_executor(common.version)
        return {
            "server_version": info.get("server_version"),
            "server_serie": info.get("server_serie"),
            "protocol_version": info.get("protocol_version"),
        }


class Json2Transport(OdooTransport):
    """Odoo 19+ JSON-2 transport (``POST /json/2/<model>/<method>``)."""

    name = "json2"

    # Methods decorated @api.model on the server: their first positional argument
    # is a normal parameter, NOT a recordset id list.
    MODEL_METHODS = frozenset(
        {
            "search",
            "search_read",
            "search_count",
            "web_search_read",
            "create",
            "name_search",
            "name_create",
            "default_get",
            "fields_get",
            "read_group",
            "formatted_read_group",
            "load",
        }
    )

    # Ordered names for the positional arguments each method accepts. For instance
    # methods the ids are handled separately, so these are the args *after* ids.
    # JSON-2 requires the exact server-side parameter names.
    POSITIONAL_PARAMS: Dict[str, List[str]] = {
        "search": ["domain"],
        "search_read": ["domain"],
        "search_count": ["domain"],
        "web_search_read": ["domain"],
        "read_group": ["domain"],
        "formatted_read_group": ["domain"],
        "create": ["vals_list"],
        "default_get": ["fields_list"],
        "name_search": ["name"],
        "fields_get": ["allfields"],
        "load": ["fields", "data"],
        # instance methods (args after the ids list):
        "read": ["fields"],
        "write": ["vals"],
        "unlink": [],
        "copy": ["default"],
        "export_data": ["fields_to_export"],
    }

    def __init__(self, settings: "Settings") -> None:
        super().__init__(settings)
        self.api_key = settings.odoo_api_key
        if not self.api_key:
            raise OdooAuthenticationError(
                "The JSON-2 transport requires an API key. Set ODOO_API_KEY "
                "(Preferences > Account Security > New API Key)."
            )
        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"bearer {self.api_key}",
            "X-Odoo-Database": self.database,
            "Content-Type": "application/json",
        }

    def _build_body(
        self,
        method: str,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Translate the positional (args, kwargs) convention into a JSON-2 body.

        JSON-2 uses named parameters at the top level, record ids under an
        ``ids`` key, and an optional ``context`` dict (which flows through from
        kwargs untouched).
        """
        args = list(args or [])
        body: Dict[str, Any] = dict(kwargs or {})
        ids: Optional[Any] = None

        # For non-@api.model methods the first positional argument is the
        # recordset the method operates on.
        if method not in self.MODEL_METHODS and args:
            ids = args.pop(0)

        names = self.POSITIONAL_PARAMS.get(method)
        for i, value in enumerate(args):
            if names is not None and i < len(names):
                body[names[i]] = value
            else:
                raise OdooRequestError(
                    f"Cannot translate positional argument #{i} of '{method}' into a "
                    f"JSON-2 named parameter. JSON-2 requires named arguments — pass "
                    f"this value via kwargs instead."
                )

        if ids is not None:
            # JSON-2 expects an array of ids.
            body["ids"] = ids if isinstance(ids, list) else [ids]

        return body

    def _post(self, url: str, body: Dict[str, Any]) -> requests.Response:
        return self._session.post(
            url, json=body, headers=self._headers(), timeout=self.timeout
        )

    @staticmethod
    def _error_detail(resp: requests.Response) -> str:
        try:
            data = resp.json()
            name = data.get("name", "")
            message = data.get("message") or resp.text
            return f"{resp.status_code} {name}: {message}".strip()
        except ValueError:
            return f"{resp.status_code}: {resp.text[:500]}"

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        body = self._build_body(method, args or [], kwargs or {})
        url = f"{self.url}/json/2/{model}/{method}"

        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._run_in_executor(self._post, url, body)
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise OdooConnectionError(
                        f"JSON-2 request to {model}.{method} failed after "
                        f"{attempt + 1} attempts: {e}"
                    ) from e
                logger.warning(
                    f"[json2] attempt {attempt + 1} for {model}.{method} failed: {e}. "
                    f"Retrying in {self.retry_delay}s..."
                )
                await asyncio.sleep(self.retry_delay)
                continue

            if resp.status_code < 300:
                return resp.json() if resp.content else None

            detail = self._error_detail(resp)
            if resp.status_code in (401, 403):
                raise OdooAuthenticationError(detail)
            if 400 <= resp.status_code < 500:
                # Client/business error — fail fast, retrying will not help.
                raise OdooRequestError(detail)
            # 5xx — transient server error, worth retrying.
            if attempt == self.max_retries:
                raise OdooConnectionError(detail)
            logger.warning(
                f"[json2] {model}.{method} returned {resp.status_code}, retrying "
                f"in {self.retry_delay}s..."
            )
            await asyncio.sleep(self.retry_delay)

    async def version(self) -> Dict[str, Any]:
        # /web/webclient/version_info is an unauthenticated JSON-RPC route that
        # exists on every Odoo version and reports the server serie.
        url = f"{self.url}/web/webclient/version_info"

        def _call() -> requests.Response:
            return self._session.post(
                url,
                json={"jsonrpc": "2.0", "method": "call", "params": {}},
                timeout=self.timeout,
            )

        resp = await self._run_in_executor(_call)
        resp.raise_for_status()
        result = resp.json().get("result", {}) or {}
        return {
            "server_version": result.get("server_version"),
            "server_serie": result.get("server_serie"),
            "protocol_version": result.get("protocol_version"),
        }

    async def check_connection(self) -> Dict[str, Any]:
        # version_info is unauthenticated, so also make a cheap authenticated call
        # to confirm the API key is actually valid.
        info: Dict[str, Any] = {}
        try:
            info = await self.version()
        except Exception as e:  # noqa: BLE001 - non-fatal, key check is what matters
            logger.debug(f"[json2] version probe failed: {e}")

        try:
            await self.execute_kw("res.users", "search_count", [[]], {})
        except Exception as e:  # noqa: BLE001
            logger.error(f"[json2] API key check failed: {e}")
            return {
                "connected": False,
                "transport": self.name,
                "database": self.database,
                "error": str(e),
                **info,
            }

        return {
            "connected": True,
            "transport": self.name,
            "database": self.database,
            **info,
        }


def resolve_transport_name(settings: "Settings") -> str:
    """Map the ``odoo_transport`` setting to a concrete transport name."""
    choice = (settings.odoo_transport or "auto").strip().lower()
    if choice == "auto":
        # JSON-2 needs an API key; without one, only XML-RPC is possible.
        return "json2" if settings.odoo_api_key else "xmlrpc"
    if choice in ("json2", "jsonrpc2", "json-2"):
        return "json2"
    if choice in ("xmlrpc", "xml-rpc", "rpc"):
        return "xmlrpc"
    raise ValueError(
        f"Unknown ODOO_TRANSPORT '{settings.odoo_transport}'. "
        f"Use 'auto', 'json2', or 'xmlrpc'."
    )


def create_transport(settings: "Settings") -> OdooTransport:
    """Build the transport selected by configuration."""
    name = resolve_transport_name(settings)
    if name == "json2":
        return Json2Transport(settings)
    return XmlRpcTransport(settings)
