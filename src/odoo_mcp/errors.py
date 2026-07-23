"""
Shared exception types for the Odoo MCP server.

Kept in their own module so both ``client`` and ``transport`` can import them
without creating a circular dependency.
"""


class OdooError(Exception):
    """Base class for all Odoo-related errors."""


class OdooAuthenticationError(OdooError):
    """Raised when authentication with Odoo fails (bad credentials / API key)."""


class OdooConnectionError(OdooError):
    """Raised when the connection to Odoo fails at the transport level."""


class OdooRequestError(OdooError):
    """Raised on a non-recoverable server-side error (validation, access rights,
    unknown method). Analogous to an XML-RPC Fault or a JSON-2 4xx response —
    retrying will not change the outcome, so callers should fail fast."""
