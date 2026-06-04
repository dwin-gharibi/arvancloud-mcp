"""Tests for observability: metrics, audit log, rate limiting."""

from __future__ import annotations

import httpx
import pytest
import respx

from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


async def test_metrics_counts_calls():
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_capabilities", {})
    m = unwrap(await mcp.call_tool("arvan_metrics", {}))
    assert m["total_calls"] >= 1
    assert "arvan_capabilities" in m["tools"]


async def test_metrics_prometheus_format():
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_capabilities", {})
    out = unwrap(await mcp.call_tool("arvan_metrics", {"prometheus": True}))
    assert isinstance(out, str)
    assert "arvan_mcp_tool_calls_total" in out


async def test_rate_limit_enforced():
    mcp, _ = build_server(make_settings(rate_limit_per_min=1))
    tm = mcp._tool_manager
    await tm.call_tool("arvan_capabilities", {})
    with pytest.raises(RuntimeError):
        await tm.call_tool("arvan_capabilities", {})


async def test_audit_log_records_mutations():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.post("https://hook.test/").mock(return_value=httpx.Response(200))
        await mcp.call_tool(
            "arvan_notify_webhook", {"url": "https://hook.test/", "text": "hi"}
        )
    log = unwrap(await mcp.call_tool("arvan_audit_log", {}))
    assert any(e["tool"] == "arvan_notify_webhook" for e in log["entries"])
    assert all(e["tool"] != "arvan_capabilities" for e in log["entries"])
