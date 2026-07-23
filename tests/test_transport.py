"""
Tests for the Odoo transports (XML-RPC and JSON-2) and transport selection.

No network is touched: the XML-RPC transport's ``_run_in_executor`` and the
JSON-2 transport's ``_post`` are mocked so we can assert on retry behaviour and
on the exact request that would go over the wire.
"""

import xmlrpc.client

import pytest
import requests
from unittest.mock import AsyncMock, MagicMock

from odoo_mcp.config import Settings
from odoo_mcp.errors import (
    OdooAuthenticationError,
    OdooConnectionError,
    OdooRequestError,
)
from odoo_mcp.transport import (
    Json2Transport,
    XmlRpcTransport,
    create_transport,
    resolve_transport_name,
)


def _settings(**overrides):
    base = dict(
        odoo_url="https://test.odoo.com",
        odoo_database="test_db",
        odoo_username="test_user",
        odoo_password="test_password",
        odoo_max_retries=2,
        odoo_retry_delay=0.0,  # keep tests fast
    )
    base.update(overrides)
    # _env_file=None keeps the test hermetic — never read the real project .env.
    return Settings(_env_file=None, **base)


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text
        self.content = b"x" if json_data is not None or text else b""

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


# --------------------------------------------------------------------------- #
# Transport selection
# --------------------------------------------------------------------------- #

def test_auto_without_api_key_is_xmlrpc():
    assert resolve_transport_name(_settings()) == "xmlrpc"


def test_auto_with_api_key_is_json2():
    assert resolve_transport_name(_settings(odoo_api_key="KEY")) == "json2"


def test_explicit_transport_overrides():
    assert resolve_transport_name(_settings(odoo_transport="xmlrpc", odoo_api_key="K")) == "xmlrpc"
    assert resolve_transport_name(_settings(odoo_transport="json2", odoo_api_key="K")) == "json2"


def test_unknown_transport_raises():
    with pytest.raises(ValueError):
        resolve_transport_name(_settings(odoo_transport="carrier-pigeon"))


def test_json2_requires_api_key():
    with pytest.raises(OdooAuthenticationError):
        create_transport(_settings(odoo_transport="json2"))  # no key


# --------------------------------------------------------------------------- #
# JSON-2 request construction
# --------------------------------------------------------------------------- #

@pytest.fixture
def json2():
    return Json2Transport(_settings(odoo_api_key="KEY"))


def test_json2_body_search_read(json2):
    body = json2._build_body("search_read", [[["is_company", "=", True]]], {"fields": ["name"]})
    assert body == {"domain": [["is_company", "=", True]], "fields": ["name"]}
    assert "ids" not in body  # @api.model method — no recordset


def test_json2_body_write_splits_ids_and_vals(json2):
    body = json2._build_body("write", [[1, 2], {"name": "X"}], {})
    assert body == {"ids": [1, 2], "vals": {"name": "X"}}


def test_json2_body_default_get_uses_fields(json2):
    # Verified against Odoo 19: the JSON-2 param is "fields", not "fields_list".
    body = json2._build_body("default_get", [["state", "company_id"]], {})
    assert body == {"fields": ["state", "company_id"]}


def test_json2_body_export_data_uses_fields_to_export(json2):
    body = json2._build_body("export_data", [[1], ["name"]], {})
    assert body == {"ids": [1], "fields_to_export": ["name"]}


def test_json2_body_normalizes_single_id(json2):
    # copy() receives a bare int id; JSON-2 always wants an array.
    body = json2._build_body("copy", [5], {"default": {"name": "c"}})
    assert body == {"ids": [5], "default": {"name": "c"}}


def test_json2_body_arbitrary_action_method_treats_arg0_as_ids(json2):
    body = json2._build_body("action_confirm", [[42]], {})
    assert body == {"ids": [42]}


def test_json2_body_rejects_unmappable_positional(json2):
    # An unknown method with a second positional arg cannot be named.
    with pytest.raises(OdooRequestError):
        json2._build_body("some_method", [[1], "extra"], {})


def test_json2_headers(json2):
    h = json2._headers()
    assert h["Authorization"] == "bearer KEY"
    assert h["X-Odoo-Database"] == "test_db"
    assert h["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_json2_execute_success(json2):
    json2._post = MagicMock(return_value=_FakeResponse(200, [{"id": 25, "name": "Deco"}]))
    result = await json2.execute_kw("res.partner", "search_read", [[]], {"fields": ["name"]})

    assert result == [{"id": 25, "name": "Deco"}]
    url, body = json2._post.call_args.args
    assert url == "https://test.odoo.com/json/2/res.partner/search_read"
    assert body == {"domain": [], "fields": ["name"]}


@pytest.mark.asyncio
async def test_json2_4xx_fails_fast(json2):
    json2._post = MagicMock(
        return_value=_FakeResponse(400, {"name": "ValidationError", "message": "bad"})
    )
    with pytest.raises(OdooRequestError):
        await json2.execute_kw("res.partner", "create", [{"x": 1}], {})
    # No retries on a client/business error.
    assert json2._post.call_count == 1


@pytest.mark.asyncio
async def test_json2_401_is_auth_error(json2):
    json2._post = MagicMock(
        return_value=_FakeResponse(401, {"name": "Unauthorized", "message": "Invalid apikey"})
    )
    with pytest.raises(OdooAuthenticationError):
        await json2.execute_kw("res.partner", "search_count", [[]], {})
    assert json2._post.call_count == 1


@pytest.mark.asyncio
async def test_json2_5xx_retries_then_raises(json2):
    json2._post = MagicMock(return_value=_FakeResponse(500, {"name": "Err", "message": "boom"}))
    with pytest.raises(OdooConnectionError):
        await json2.execute_kw("res.partner", "search_count", [[]], {})
    # max_retries=2 -> 3 attempts.
    assert json2._post.call_count == 3


@pytest.mark.asyncio
async def test_json2_connection_error_retries(json2):
    json2._post = MagicMock(side_effect=requests.ConnectionError("down"))
    with pytest.raises(OdooConnectionError):
        await json2.execute_kw("res.partner", "search_count", [[]], {})
    assert json2._post.call_count == 3


# --------------------------------------------------------------------------- #
# XML-RPC retry / error semantics
# --------------------------------------------------------------------------- #

@pytest.fixture
def xmlrpc_transport():
    t = XmlRpcTransport(_settings())
    # Pretend we are already authenticated so execute_kw goes straight to the call.
    t.uid = 1
    t._models = MagicMock()
    t._run_in_executor = AsyncMock()
    return t


@pytest.mark.asyncio
async def test_xmlrpc_fault_fails_fast(xmlrpc_transport):
    xmlrpc_transport._run_in_executor.side_effect = xmlrpc.client.Fault(2, "Access Denied")
    with pytest.raises(OdooRequestError):
        await xmlrpc_transport.execute_kw("res.partner", "read", [[1]], {})
    assert xmlrpc_transport._run_in_executor.await_count == 1


@pytest.mark.asyncio
async def test_xmlrpc_transport_error_retries(xmlrpc_transport):
    xmlrpc_transport._run_in_executor.side_effect = ConnectionError("network down")
    with pytest.raises(OdooConnectionError):
        await xmlrpc_transport.execute_kw("res.partner", "read", [[1]], {})
    assert xmlrpc_transport._run_in_executor.await_count == 3


@pytest.mark.asyncio
async def test_xmlrpc_recovers_after_transient_error(xmlrpc_transport):
    xmlrpc_transport._run_in_executor.side_effect = [
        ConnectionError("blip"),
        [{"id": 1, "name": "ACME"}],
    ]
    result = await xmlrpc_transport.execute_kw("res.partner", "read", [[1]], {})
    assert result == [{"id": 1, "name": "ACME"}]
    assert xmlrpc_transport._run_in_executor.await_count == 2
