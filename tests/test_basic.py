"""
Basic tests for the Odoo MCP server functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from odoo_mcp.client import OdooClient, OdooError
from odoo_mcp.config import Settings
from odoo_mcp.tools import search_records_tool, create_record_tool


@pytest.fixture
def mock_odoo_client():
    """Create a mock Odoo client for testing."""
    client = AsyncMock(spec=OdooClient)
    return client


@pytest.mark.asyncio
async def test_search_records_tool_success(mock_odoo_client):
    """Test successful record search."""
    # Mock the client's search_records method
    mock_records = [{"id": 1, "name": "Test Record"}]
    mock_odoo_client.search_records.return_value = mock_records
    
    result = await search_records_tool(
        client=mock_odoo_client,
        model="res.partner",
        domain=[("name", "=", "Test")],
        fields=["id", "name"],
    )
    
    assert result["success"] is True
    assert result["model"] == "res.partner"
    assert result["count"] == 1
    assert result["records"] == mock_records


@pytest.mark.asyncio
async def test_search_records_tool_error(mock_odoo_client):
    """Test record search with Odoo error."""
    # Mock the client to raise an OdooError
    mock_odoo_client.search_records.side_effect = OdooError("Access denied")
    
    result = await search_records_tool(
        client=mock_odoo_client,
        model="res.partner",
    )
    
    assert result["success"] is False
    assert result["error"] == "Access denied"
    assert result["error_type"] == "OdooError"


@pytest.mark.asyncio
async def test_create_record_tool_success(mock_odoo_client):
    """Test successful record creation."""
    # Mock the client's create_record method
    mock_odoo_client.create_record.return_value = 123
    
    values = {"name": "New Partner", "email": "test@example.com"}
    result = await create_record_tool(
        client=mock_odoo_client,
        model="res.partner",
        values=values,
    )
    
    assert result["success"] is True
    assert result["model"] == "res.partner"
    assert result["record_id"] == 123
    assert result["values"] == values


@pytest.mark.asyncio
async def test_create_record_tool_error(mock_odoo_client):
    """Test record creation with error."""
    # Mock the client to raise an OdooError
    mock_odoo_client.create_record.side_effect = OdooError("Validation error")
    
    result = await create_record_tool(
        client=mock_odoo_client,
        model="res.partner",
        values={"name": "Test"},
    )
    
    assert result["success"] is False
    assert result["error"] == "Validation error"
    assert result["error_type"] == "OdooError"


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