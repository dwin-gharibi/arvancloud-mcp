"""Tests for the low-level ArvanCloud HTTP client."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from arvancloud_mcp.client import ArvanAPIError, ArvanClient, _clean_params

from .conftest import TEST_BASE_URL, make_settings


def test_clean_params_drops_none_and_renders_bools():
    assert _clean_params({"a": None, "b": True, "c": 1, "d": False}) == {
        "b": "true",
        "c": 1,
        "d": "false",
    }
    assert _clean_params(None) is None
    assert _clean_params({"only": None}) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("abc123", "Apikey abc123"),
        ("Apikey abc123", "Apikey abc123"),
        ("apikey abc123", "Apikey abc123"),
        ("  apikey   abc123 ", "Apikey abc123"),
        ("", ""),
    ],
)
def test_authorization_normalisation(raw, expected):
    client = ArvanClient(make_settings(api_key=raw))
    assert client._authorization() == expected


async def test_request_sends_auth_and_accept_headers():
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.get("/ecc/v1/regions").mock(
            return_value=httpx.Response(200, json={"data": [{"code": "ir-thr-c2"}]})
        )
        client = ArvanClient(make_settings())
        result = await client.request("GET", "/ecc/v1/regions")
        await client.aclose()

    assert result == {"data": [{"code": "ir-thr-c2"}]}
    request = route.calls.last.request
    assert request.headers["authorization"] == "Apikey testkey"
    assert request.headers["accept"] == "application/json"
    assert "arvancloud-mcp/" in request.headers["user-agent"]


async def test_post_sends_json_body():
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/cdn/4.0/domains").mock(
            return_value=httpx.Response(201, json={"data": {"id": "1"}})
        )
        client = ArvanClient(make_settings())
        await client.request("POST", "/cdn/4.0/domains", json={"domain": "x.com"})
        await client.aclose()

    assert json.loads(route.calls.last.request.content) == {"domain": "x.com"}


async def test_retries_then_succeeds_on_transient_error():
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.get("/flaky").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(429),
                httpx.Response(200, json={"ok": True}),
            ]
        )
        client = ArvanClient(make_settings(max_retries=3))
        result = await client.request("GET", "/flaky")
        await client.aclose()

    assert result == {"ok": True}
    assert route.call_count == 3


async def test_retries_exhausted_on_network_error():
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/down").mock(side_effect=httpx.ConnectError("boom"))
        client = ArvanClient(make_settings(max_retries=1))
        with pytest.raises(ArvanAPIError) as excinfo:
            await client.request("GET", "/down")
        await client.aclose()

    assert "network error" in str(excinfo.value)


async def test_api_error_parses_message_and_status():
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/missing").mock(
            return_value=httpx.Response(404, json={"message": "not found"})
        )
        client = ArvanClient(make_settings())
        with pytest.raises(ArvanAPIError) as excinfo:
            await client.request("GET", "/missing")
        await client.aclose()

    err = excinfo.value
    assert err.status_code == 404
    assert "not found" in str(err)


async def test_missing_api_key_raises_before_request():
    client = ArvanClient(make_settings(api_key=""))
    with pytest.raises(ArvanAPIError) as excinfo:
        await client.request("GET", "/ecc/v1/regions")
    assert "API key" in str(excinfo.value)


async def test_empty_body_returns_ok_marker():
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.delete("/ecc/v1/regions/ir-thr-c2/ptr/1").mock(
            return_value=httpx.Response(204)
        )
        client = ArvanClient(make_settings())
        result = await client.request(
            "DELETE", "/ecc/v1/regions/ir-thr-c2/ptr/1"
        )
        await client.aclose()

    assert result == {"status": 204, "ok": True}
