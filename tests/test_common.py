"""Tests for the common tools: generic request, capabilities, doctor."""

from __future__ import annotations

import httpx
import respx

from arvancloud_mcp.server import build_server

from .conftest import TEST_BASE_URL, make_settings, unwrap


async def test_capabilities_overview_and_service_detail():
    mcp, _ = build_server(make_settings())
    overview = unwrap(await mcp.call_tool("arvan_capabilities", {}))
    assert "services" in overview
    assert "compute" in overview["services"]

    detail = unwrap(await mcp.call_tool("arvan_capabilities", {"service": "k8s"}))
    assert detail["service"] == "k8s"
    assert detail["endpoints"]


async def test_capabilities_unknown_service():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_capabilities", {"service": "nope"}))
    assert "error" in out
    assert "compute" in out["available"]


async def test_doctor_reports_api_ok_and_tools():
    mcp, _ = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/ecc/v1/regions").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        out = unwrap(await mcp.call_tool("arvan_doctor", {}))
    assert out["api"]["ok"] is True
    assert "tools" in out and "terraform" in out["tools"]
    assert "object_storage" in out and "ssh" in out


async def test_doctor_reports_api_failure():
    mcp, _ = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/ecc/v1/regions").mock(
            return_value=httpx.Response(401, json={"message": "unauthorized"})
        )
        out = unwrap(await mcp.call_tool("arvan_doctor", {}))
    assert out["api"]["ok"] is False
    assert "unauthorized" in out["api"]["error"]


async def test_doctor_no_api_key():
    mcp, _ = build_server(make_settings(api_key=""))
    out = unwrap(await mcp.call_tool("arvan_doctor", {}))
    assert out["api"]["configured"] is False


async def test_prompts_registered():
    mcp, _ = build_server(make_settings())
    prompts = {p.name for p in await mcp.list_prompts()}
    assert "provision_web_server" in prompts
    assert "setup_cdn" in prompts
    assert "deploy_static_site" in prompts


async def test_resources_registered_and_readable():
    mcp, _ = build_server(make_settings())
    uris = {str(r.uri) for r in await mcp.list_resources()}
    assert "arvan://capabilities" in uris
    assert "arvan://regions" in uris

    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/ecc/v1/regions").mock(
            return_value=httpx.Response(200, json={"data": ["r1"]})
        )
        contents = await mcp.read_resource("arvan://regions")
    assert contents
