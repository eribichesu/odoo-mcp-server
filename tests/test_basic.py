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


@pytest.mark.asyncio
async def test_read_group_legacy_on_old_odoo(client):
    """On Odoo <18 read_group() calls the legacy 'read_group' method."""
    client._use_formatted_read_group = AsyncMock(return_value=False)
    client._execute_kw.return_value = []

    await client.read_group(
        "sale.order", domain=[], fields=["amount_total:sum"], groupby=["state"]
    )

    method = client._execute_kw.await_args.args[1]
    kwargs = client._execute_kw.await_args.args[3]
    assert method == "read_group"
    assert "lazy" in kwargs  # legacy-only arg
    assert kwargs["fields"] == ["amount_total:sum"]


@pytest.mark.asyncio
async def test_read_group_uses_formatted_on_odoo_19(client):
    """On Odoo 18+ read_group() routes to 'formatted_read_group' with split args."""
    client._use_formatted_read_group = AsyncMock(return_value=True)
    client._execute_kw.return_value = []

    await client.read_group(
        "sale.order",
        domain=[],
        fields=["state", "amount_total:sum"],  # 'state' is a group field, not an aggregate
        groupby=["state"],
        orderby="amount_total:sum desc",
    )

    method = client._execute_kw.await_args.args[1]
    kwargs = client._execute_kw.await_args.args[3]
    assert method == "formatted_read_group"
    # bare group-field names are dropped; only aggregate specs (+ __count) remain
    assert kwargs["aggregates"] == ["amount_total:sum", "__count"]
    assert kwargs["groupby"] == ["state"]
    assert kwargs["order"] == "amount_total:sum desc"  # 'order', not 'orderby'
    assert "lazy" not in kwargs


@pytest.mark.asyncio
async def test_read_group_formatted_always_requests_count(client):
    """Count-only grouping must still request __count (formatted omits it otherwise)."""
    client._use_formatted_read_group = AsyncMock(return_value=True)
    client._execute_kw.return_value = []

    await client.read_group("res.partner", domain=[], fields=[], groupby=["country_id"])

    kwargs = client._execute_kw.await_args.args[3]
    assert kwargs["aggregates"] == ["__count"]


@pytest.mark.asyncio
async def test_use_formatted_read_group_true_for_json2():
    """A JSON-2 transport implies Odoo 19+, so formatted_read_group is used."""
    settings = Settings(
        _env_file=None,
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
        odoo_api_key="KEY",  # -> json2
    )
    client = OdooClient(settings)
    assert client.transport_name == "json2"
    assert await client._use_formatted_read_group() is True


@pytest.mark.parametrize(
    "serie,expected",
    [
        ("saas~19.3", True),   # Odoo Online serie — must not fail to parse
        ("saas~18.2", True),
        ("19.0", True),
        ("18.0", True),
        ("17.0", False),
        ("saas~16.4", False),
        ("", False),
    ],
)
@pytest.mark.asyncio
async def test_use_formatted_read_group_parses_serie_over_xmlrpc(serie, expected):
    """Over XML-RPC the serie decides, and SaaS series ('saas~19.3') must parse.

    A parse failure here silently routes grouping to read_group, which no longer
    exists on Odoo 19.
    """
    settings = Settings(
        _env_file=None,
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
        odoo_transport="xmlrpc",
    )
    client = OdooClient(settings)
    client._transport.version = AsyncMock(return_value={"server_serie": serie})
    assert await client._use_formatted_read_group() is expected


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

# --- MCP tool layer: load_odoo_data / search_odoo_records_two_step -----------


@pytest.fixture
def server(monkeypatch):
    """The server module with get_odoo_client() patched to a mocked OdooClient."""
    import odoo_mcp.server as srv

    fake = AsyncMock()
    monkeypatch.setattr(srv, "get_odoo_client", AsyncMock(return_value=fake))
    return srv, fake


@pytest.mark.asyncio
async def test_load_tool_passes_fields_and_rows(server):
    """load_odoo_data forwards parsed headers and rows, and reports the ids."""
    srv, fake = server
    fake.get_model_fields.return_value = {"name": {"type": "char"}}
    fake.load_data.return_value = {"ids": [1, 2], "messages": []}

    result = await srv.load_odoo_data("res.partner", "name", '[["A"],["B"]]')

    fake.load_data.assert_awaited_once_with("res.partner", ["name"], [["A"], ["B"]])
    assert result["ids"] == [1, 2]
    assert result["loaded"] == 2
    assert result["success"] is True


@pytest.mark.asyncio
async def test_load_tool_rejects_unknown_column(server):
    """A typo'd header is caught locally — Odoo 19 turns it into an opaque 500."""
    srv, fake = server
    fake.get_model_fields.return_value = {"name": {"type": "char"}}

    result = await srv.load_odoo_data("res.partner", "name,nope", '[["A","x"]]')

    assert "nope" in result["error"]
    fake.load_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_tool_accepts_importer_paths(server):
    """'country_id/id' is valid: only the part before '/' names a field."""
    srv, fake = server
    fake.get_model_fields.return_value = {"name": {}, "country_id": {}}
    fake.load_data.return_value = {"ids": [5], "messages": []}

    result = await srv.load_odoo_data("res.partner", "id,name,country_id/id", '[["m.x","A","base.it"]]')

    assert result["success"] is True
    assert fake.load_data.await_args.args[1] == ["id", "name", "country_id/id"]


@pytest.mark.asyncio
async def test_load_tool_rejects_row_width_mismatch(server):
    """Row width must match the header count, or values land in the wrong column."""
    srv, fake = server
    fake.get_model_fields.return_value = {"name": {}, "color": {}}

    result = await srv.load_odoo_data("res.partner", "name,color", '[["A"]]')

    assert "exactly 2 values" in result["error"]
    fake.load_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_tool_reports_error_messages_as_failure(server):
    """An error-level message means the load was rejected, even if ids came back."""
    srv, fake = server
    fake.get_model_fields.return_value = {"name": {}}
    fake.load_data.return_value = {
        "ids": [1],
        "messages": [{"type": "error", "message": "bad value"}],
    }

    result = await srv.load_odoo_data("res.partner", "name", '[["A"]]')

    assert result["success"] is False
    assert result["messages"][0]["message"] == "bad value"


@pytest.mark.asyncio
async def test_two_step_tool_uses_search_records(server):
    """search_odoo_records_two_step routes to the search+read client method."""
    srv, fake = server
    fake.search_records.return_value = [{"id": 1, "name": "A"}]

    result = await srv.search_odoo_records_two_step(
        "res.partner", '[["is_company","=",true]]', "name", limit=5, offset=2, order="name ASC"
    )

    fake.search_records.assert_awaited_once_with(
        model="res.partner",
        domain=[["is_company", "=", True]],
        fields=["name"],
        limit=5,
        offset=2,
        order="name ASC",
    )
    assert result["count"] == 1
