"""
Basic tests for the Odoo MCP server functionality.
"""

import xmlrpc.client

import pytest
from unittest.mock import AsyncMock, MagicMock
from odoo_mcp.client import OdooClient, OdooError
from odoo_mcp.config import Settings


@pytest.fixture
def client():
    """Create an OdooClient with a mocked, already-authenticated RPC layer."""
    settings = Settings(
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
    )
    client = OdooClient(settings)
    # Bypass the real network authentication handshake.
    client._authenticated = True
    client.uid = 1
    client._execute_kw = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_search_read_success(client):
    """search_read returns the records from the RPC layer."""
    mock_records = [{"id": 1, "name": "Test Record"}]
    client._execute_kw.return_value = mock_records

    records = await client.search_read(
        model="res.partner",
        domain=[("name", "=", "Test")],
        fields=["id", "name"],
    )

    assert records == mock_records
    client._execute_kw.assert_awaited_once()
    # search_read must go through a single RPC call, not search + read.
    assert client._execute_kw.await_args.args[1] == "search_read"


@pytest.mark.asyncio
async def test_search_read_wraps_errors(client):
    """A failing RPC call is wrapped in OdooError."""
    client._execute_kw.side_effect = RuntimeError("Access denied")

    with pytest.raises(OdooError, match="Access denied"):
        await client.search_read(model="res.partner")


@pytest.mark.asyncio
async def test_create_record_success(client):
    """create_record returns the new record id."""
    client._execute_kw.return_value = 123

    record_id = await client.create_record(
        "res.partner", {"name": "New Partner", "email": "test@example.com"}
    )

    assert record_id == 123
    assert client._execute_kw.await_args.args[1] == "create"


@pytest.mark.asyncio
async def test_create_record_wraps_errors(client):
    """A validation failure surfaces as OdooError."""
    client._execute_kw.side_effect = RuntimeError("Validation error")

    with pytest.raises(OdooError, match="Validation error"):
        await client.create_record("res.partner", {"name": "Test"})


@pytest.fixture
def rpc_client():
    """OdooClient authenticated, with only the RPC transport (_run_in_executor) mocked.

    This exercises the real _execute_kw retry logic instead of stubbing it out.
    """
    settings = Settings(
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
        odoo_max_retries=2,
        odoo_retry_delay=0.0,  # keep the test fast
    )
    client = OdooClient(settings)
    client._authenticated = True
    client.uid = 1
    client._models = MagicMock()  # .execute_kw is read but the call is mocked out
    client._run_in_executor = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_execute_kw_does_not_retry_server_faults(rpc_client):
    """A server-side Fault (validation/access) must fail fast, not retry."""
    rpc_client._run_in_executor.side_effect = xmlrpc.client.Fault(2, "Access Denied")

    with pytest.raises(xmlrpc.client.Fault):
        await rpc_client._execute_kw("res.partner", "read", [[1]])

    # Called exactly once — no wasted retries on a non-recoverable error.
    assert rpc_client._run_in_executor.await_count == 1


@pytest.mark.asyncio
async def test_execute_kw_retries_transport_errors(rpc_client):
    """A transport/connection error is retried up to max_retries + 1 attempts."""
    rpc_client._run_in_executor.side_effect = ConnectionError("network down")

    with pytest.raises(ConnectionError):
        await rpc_client._execute_kw("res.partner", "read", [[1]])

    # max_retries=2 -> 3 total attempts.
    assert rpc_client._run_in_executor.await_count == 3


@pytest.mark.asyncio
async def test_execute_kw_recovers_after_transient_error(rpc_client):
    """A transient transport error followed by success returns the result."""
    rpc_client._run_in_executor.side_effect = [
        ConnectionError("blip"),
        [{"id": 1, "name": "ACME"}],
    ]

    result = await rpc_client._execute_kw("res.partner", "read", [[1]])

    assert result == [{"id": 1, "name": "ACME"}]
    assert rpc_client._run_in_executor.await_count == 2


def test_settings_validation():
    """Test that settings are properly validated."""
    settings = Settings(
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
    )
    
    assert settings.odoo_url == "https://test.odoo.com"
    assert settings.odoo_database == "test_db"
    assert settings.odoo_username == "test_user"
    assert settings.odoo_password == "test_password"
    assert settings.server_name == "odoo-mcp"


def test_settings_from_env(monkeypatch):
    """Test settings loading from environment variables."""
    monkeypatch.setenv("ODOO_URL", "https://env.odoo.com")
    monkeypatch.setenv("ODOO_DATABASE", "env_db")
    monkeypatch.setenv("ODOO_USERNAME", "env_user")
    monkeypatch.setenv("ODOO_PASSWORD", "env_password")
    
    settings = Settings()
    
    assert settings.odoo_url == "https://env.odoo.com"
    assert settings.odoo_database == "env_db"
    assert settings.odoo_username == "env_user"
    assert settings.odoo_password == "env_password"