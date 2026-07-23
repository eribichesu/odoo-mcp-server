"""
Basic tests for the Odoo MCP server functionality.

Transport-level behaviour (retries, JSON-2/XML-RPC wire format) lives in
``test_transport.py``.
"""

import pytest
from unittest.mock import AsyncMock
from odoo_mcp.client import OdooClient, OdooError
from odoo_mcp.config import Settings


@pytest.fixture
def client():
    """OdooClient with the transport call layer (_execute_kw) mocked out."""
    settings = Settings(
        _env_file=None,  # hermetic: ignore the real project .env
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
    )
    client = OdooClient(settings)
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


@pytest.mark.asyncio
async def test_create_record_normalizes_json2_list_result(client):
    """JSON-2 create() returns a list of ids; create_record must return a bare id."""
    client._execute_kw.return_value = [226]  # create-multi semantics
    record_id = await client.create_record("res.partner", {"name": "ACME"})
    assert record_id == 226


@pytest.mark.asyncio
async def test_copy_record_normalizes_json2_list_result(client):
    """JSON-2 copy() likewise returns a list; copy_record must return a bare id."""
    client._execute_kw.return_value = [227]
    new_id = await client.copy_record("res.partner", 226, {"name": "copy"})
    assert new_id == 227


@pytest.mark.asyncio
async def test_create_record_keeps_xmlrpc_int_result(client):
    """XML-RPC create() returns a bare int, which must pass through unchanged."""
    client._execute_kw.return_value = 42
    record_id = await client.create_record("res.partner", {"name": "ACME"})
    assert record_id == 42


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