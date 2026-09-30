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


# --- MCP tool layer: attachments --------------------------------------------


@pytest.fixture
def download_dir(server, tmp_path, monkeypatch):
    """Point downloads at a temp dir so tests never touch ~/Downloads."""
    srv, _ = server
    monkeypatch.setattr(srv.settings, "download_dir", tmp_path)
    return tmp_path


@pytest.mark.asyncio
async def test_list_attachments_defaults_to_bills(server):
    """list_odoo_attachments targets account.move unless told otherwise."""
    srv, fake = server
    fake.list_attachments.return_value = [{"id": 7, "name": "bill.pdf"}]

    result = await srv.list_odoo_attachments(42)

    fake.list_attachments.assert_awaited_once_with("account.move", 42)
    assert result["count"] == 1
    assert result["attachments"][0]["id"] == 7


@pytest.mark.asyncio
async def test_download_attachment_writes_file(server, download_dir):
    """The decoded content is saved under the download dir, id-prefixed."""
    srv, fake = server
    fake.read_attachment.return_value = {
        "name": "bill.pdf", "type": "binary", "file_size": 5,
        "mimetype": "application/pdf", "res_model": "account.move", "res_id": 42,
    }
    fake.read_attachment_content.return_value = b"%PDF-"

    result = await srv.download_odoo_attachment(7)

    assert result["path"] == str(download_dir / "7_bill.pdf")
    assert (download_dir / "7_bill.pdf").read_bytes() == b"%PDF-"
    assert result["size"] == 5


@pytest.mark.asyncio
async def test_download_attachment_sanitizes_name(server, download_dir):
    """A name with path components cannot escape the download dir."""
    srv, fake = server
    fake.read_attachment.return_value = {"name": "../../etc/passwd", "type": "binary", "file_size": 1}
    fake.read_attachment_content.return_value = b"x"

    result = await srv.download_odoo_attachment(3)

    assert result["path"] == str(download_dir / "3_passwd")


@pytest.mark.asyncio
async def test_download_attachment_refuses_oversized(server, download_dir, monkeypatch):
    """Oversized files are refused before their content is requested."""
    srv, fake = server
    monkeypatch.setattr(srv.settings, "max_attachment_bytes", 10)
    fake.read_attachment.return_value = {"name": "big.pdf", "type": "binary", "file_size": 11}

    result = await srv.download_odoo_attachment(9)

    assert "limit" in result["error"]
    fake.read_attachment_content.assert_not_awaited()
    assert not any(download_dir.iterdir())


@pytest.mark.asyncio
async def test_download_attachment_url_type_returns_link(server, download_dir):
    """URL attachments have no stored file, so the link is returned instead."""
    srv, fake = server
    fake.read_attachment.return_value = {"name": "Portal", "type": "url", "url": "https://x"}

    result = await srv.download_odoo_attachment(4)

    assert result["url"] == "https://x"
    assert "path" not in result
    fake.read_attachment_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_attachment_not_found(server, download_dir):
    srv, fake = server
    fake.read_attachment.return_value = None

    result = await srv.download_odoo_attachment(404)

    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_download_attachment_refuses_size_mismatch(server, download_dir):
    """A short read must not be saved as if it were the whole file."""
    srv, fake = server
    fake.read_attachment.return_value = {"name": "bill.pdf", "type": "binary", "file_size": 10}
    fake.read_attachment_content.return_value = b"short"

    result = await srv.download_odoo_attachment(7)

    assert "truncated" in result["error"]
    assert not any(download_dir.iterdir())


# --- OdooClient.read_attachment_content -------------------------------------


@pytest.mark.asyncio
async def test_attachment_content_prefers_raw(client):
    """Odoo 19 has no 'datas' field, so 'raw' must be read when available."""
    import base64

    client._execute_kw.side_effect = [
        {"raw": {"type": "binary"}, "db_datas": {"type": "binary"}},  # fields_get
        [{"id": 7, "raw": base64.b64encode(b"%PDF-1.7").decode()}],
    ]

    content = await client.read_attachment_content(7)

    assert content == b"%PDF-1.7"
    assert client._execute_kw.await_args.args[3]["fields"] == ["raw"]


@pytest.mark.asyncio
async def test_attachment_content_falls_back_to_datas(client):
    """Odoo <= 13 has only 'datas'."""
    import base64

    client._execute_kw.side_effect = [
        {"datas": {"type": "binary"}},
        [{"id": 7, "datas": base64.b64encode(b"abc").decode()}],
    ]

    assert await client.read_attachment_content(7) == b"abc"
    assert client._execute_kw.await_args.args[3]["fields"] == ["datas"]


@pytest.mark.asyncio
async def test_attachment_content_accepts_xmlrpc_binary(client):
    """XML-RPC can return an xmlrpc.client.Binary holding undecoded bytes."""
    import xmlrpc.client

    client._execute_kw.side_effect = [
        {"raw": {"type": "binary"}},
        [{"id": 7, "raw": xmlrpc.client.Binary(b"\x00\x01")}],
    ]

    assert await client.read_attachment_content(7) == b"\x00\x01"


@pytest.mark.asyncio
async def test_attachment_content_field_is_cached(client):
    """fields_get runs once per client, not once per download."""
    client._execute_kw.side_effect = [
        {"raw": {"type": "binary"}},
        [{"id": 1, "raw": False}],
        [{"id": 2, "raw": False}],
    ]

    assert await client.read_attachment_content(1) is None
    assert await client.read_attachment_content(2) is None
    assert client._execute_kw.await_count == 3
