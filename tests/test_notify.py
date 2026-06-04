"""Tests for the notification tools."""

from __future__ import annotations

import httpx
import respx

from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


async def test_notify_slack():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        route = mock.post("https://hooks.slack.test/x").mock(
            return_value=httpx.Response(200)
        )
        out = unwrap(
            await mcp.call_tool(
                "arvan_notify_slack",
                {"text": "hello", "webhook_url": "https://hooks.slack.test/x"},
            )
        )
    assert out["ok"] is True
    assert route.called


async def test_notify_slack_without_url(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_notify_slack", {"text": "hello"}))
    assert out["ok"] is False


async def test_notify_telegram():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
            return_value=httpx.Response(200)
        )
        out = unwrap(
            await mcp.call_tool(
                "arvan_notify_telegram",
                {"text": "hi", "chat_id": "42", "bot_token": "TOKEN"},
            )
        )
    assert out["ok"] is True


async def test_notify_webhook():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        route = mock.post("https://hook.test/notify").mock(
            return_value=httpx.Response(202)
        )
        out = unwrap(
            await mcp.call_tool(
                "arvan_notify_webhook",
                {"url": "https://hook.test/notify", "payload": {"a": 1}},
            )
        )
    assert out["ok"] is True
    assert route.called
