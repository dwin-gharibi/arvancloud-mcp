"""Tests for the networking-diagnostics tools."""

from __future__ import annotations

import asyncio
import socket

import httpx
import respx

import arvancloud_mcp.tools.net as netmod
from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


async def test_http_check(monkeypatch):
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://svc.test/health").mock(
            return_value=httpx.Response(200, headers={"server": "nginx"})
        )
        out = unwrap(
            await mcp.call_tool("arvan_net_http_check", {"url": "https://svc.test/health"})
        )
    assert out["ok"] is True
    assert out["status_code"] == 200
    assert out["server"] == "nginx"


async def test_http_load_test():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://svc.test/").mock(return_value=httpx.Response(200))
        out = unwrap(
            await mcp.call_tool(
                "arvan_net_http_load_test",
                {"url": "https://svc.test/", "requests": 8, "concurrency": 4},
            )
        )
    assert out["successful"] == 8
    assert out["errors"] == 0
    assert out["latency_ms"]["p95"] is not None


async def test_tcp_check_open_then_closed():
    server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool("arvan_net_tcp_check", {"host": "127.0.0.1", "port": port})
    )
    assert out["open"] is True
    assert out["latency_ms"] >= 0

    server.close()
    await server.wait_closed()
    closed = unwrap(
        await mcp.call_tool(
            "arvan_net_tcp_check",
            {"host": "127.0.0.1", "port": port, "timeout": 0.5},
        )
    )
    assert closed["open"] is False


async def test_dns_lookup(monkeypatch):
    class _Rec:
        def to_text(self):
            return "1.2.3.4"

    class _RRset:
        ttl = 300

    class _Answers(list):
        rrset = _RRset()

    class _FakeResolver:
        def __init__(self, configure=True):
            self.nameservers: list[str] = []
            self.lifetime = 0.0
            self.timeout = 0.0

        def resolve(self, name, rtype):
            ans = _Answers()
            ans.append(_Rec())
            return ans

    import dns.resolver

    monkeypatch.setattr(dns.resolver, "Resolver", _FakeResolver)
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool("arvan_net_dns_lookup", {"name": "example.com", "record_type": "A"})
    )
    assert out["records"] == ["1.2.3.4"]
    assert out["ttl"] == 300


async def test_reverse_dns(monkeypatch):
    monkeypatch.setattr(
        socket, "gethostbyaddr", lambda ip: ("host.example.com", [], [ip])
    )
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_net_reverse_dns", {"ip": "1.2.3.4"}))
    assert out["hostname"] == "host.example.com"


async def test_ping_builds_command(monkeypatch):
    calls = []

    async def fake_run(cmd, **kw):
        calls.append(list(cmd))
        return {"installed": True, "ok": True, "stdout": "pong"}

    monkeypatch.setattr(netmod, "run_command", fake_run)
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_net_ping", {"host": "1.2.3.4", "count": 2}))
    assert out["ok"] is True
    assert calls[-1][0] == "ping"
    assert "1.2.3.4" in calls[-1]


async def test_tls_cert_unreachable_returns_error():
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool(
            "arvan_net_tls_cert", {"host": "127.0.0.1", "port": 1, "timeout": 0.5}
        )
    )
    assert "error" in out


async def test_my_public_ip():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://api.ipify.org").mock(
            return_value=httpx.Response(200, json={"ip": "203.0.113.7"})
        )
        out = unwrap(await mcp.call_tool("arvan_net_my_public_ip", {}))
    assert out["ip"] == "203.0.113.7"
