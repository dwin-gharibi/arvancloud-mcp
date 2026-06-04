"""Tests for the documentation search/fetch tools."""

from __future__ import annotations

import httpx
import respx

from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


async def test_docs_search_finds_dns():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_docs_search", {"query": "dns records"}))
    assert out["results"]
    assert any("dns" in r["url"].lower() for r in out["results"])


async def test_docs_topics():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_docs_topics", {}))
    assert len(out["topics"]) > 5


async def test_docs_fetch_rejects_foreign_host():
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool("arvan_docs_fetch", {"url": "https://evil.example.com/x"})
    )
    assert out["ok"] is False


async def test_docs_fetch_strips_html():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://docs.arvancloud.ir/en/cdn/").mock(
            return_value=httpx.Response(
                200, text="<html><body><h1>CDN</h1><p>Hello &amp; welcome</p></body></html>"
            )
        )
        out = unwrap(
            await mcp.call_tool(
                "arvan_docs_fetch", {"url": "https://docs.arvancloud.ir/en/cdn/"}
            )
        )
    assert out["ok"] is True
    assert "CDN" in out["content"]
    assert "Hello & welcome" in out["content"]
    assert "<" not in out["content"]


async def test_find_tool():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_find_tool", {"query": "floating ip"}))
    names = {m["tool"] for m in out["matches"]}
    assert any("floating_ip" in n for n in names)
