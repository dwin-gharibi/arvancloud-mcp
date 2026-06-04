"""Tests for background tasks & scheduling."""

from __future__ import annotations

import asyncio

import httpx
import respx

from arvancloud_mcp.server import build_server
from arvancloud_mcp.tools.tasks import TaskManager

from .conftest import make_settings, unwrap


async def _wait(predicate, timeout=5.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return predicate()


async def test_manager_runs_oneshot():
    seen = []

    async def runner(tool, args):
        seen.append((tool, args))
        return {"value": 42}

    tm = TaskManager(runner)
    rec = tm.submit("mytool", {"a": 1})
    assert await _wait(lambda: tm.get(rec.id).status == "succeeded")
    assert tm.get(rec.id).last_result == {"value": 42}
    assert seen == [("mytool", {"a": 1})]
    await tm.aclose()


async def test_manager_records_failure():
    async def runner(tool, args):
        raise RuntimeError("boom")

    tm = TaskManager(runner)
    rec = tm.submit("x", {})
    assert await _wait(lambda: tm.get(rec.id).status == "failed")
    assert "boom" in tm.get(rec.id).last_error
    await tm.aclose()


async def test_manager_recurring_then_cancel():
    runs = {"n": 0}

    async def runner(tool, args):
        runs["n"] += 1
        return runs["n"]

    tm = TaskManager(runner)
    rec = tm.submit("t", {}, interval=1.0)
    assert await _wait(lambda: rec.runs >= 1)
    assert tm.cancel(rec.id) is True
    await tm.aclose()
    assert rec.status == "cancelled"


async def test_manager_blocks_task_tools():
    async def runner(tool, args):
        return None

    tm = TaskManager(runner)
    try:
        import pytest

        with pytest.raises(ValueError):
            tm.submit("arvan_task_list", {})
    finally:
        await tm.aclose()


async def test_task_submit_status_and_webhook():
    mcp, _ = build_server(make_settings())
    try:
        async with respx.mock(assert_all_called=False) as mock:
            hook = mock.post("https://hook.test/notify").mock(
                return_value=httpx.Response(200)
            )
            sub = unwrap(
                await mcp.call_tool(
                    "arvan_task_submit",
                    {"tool": "arvan_capabilities", "announce_webhook": "https://hook.test/notify"},
                )
            )
            assert sub["ok"] is True
            task_id = sub["id"]

            async def _done():
                st = unwrap(await mcp.call_tool("arvan_task_status", {"task_id": task_id}))
                return st["status"] in ("succeeded", "failed")

            ok = False
            for _ in range(200):
                if await _done():
                    ok = True
                    break
                await asyncio.sleep(0.02)
            assert ok

            status = unwrap(await mcp.call_tool("arvan_task_status", {"task_id": task_id}))
            assert status["status"] == "succeeded"
            assert isinstance(status["last_result"], dict)
            assert hook.called

            listing = unwrap(await mcp.call_tool("arvan_task_list", {}))
            assert any(t["id"] == task_id for t in listing["tasks"])
    finally:
        await mcp._arvan_task_manager.aclose()


async def test_task_submit_rejects_task_tool():
    mcp, _ = build_server(make_settings())
    try:
        out = unwrap(
            await mcp.call_tool("arvan_task_submit", {"tool": "arvan_task_cancel"})
        )
        assert out["ok"] is False
    finally:
        await mcp._arvan_task_manager.aclose()
