"""Tests for guardrails: classification, annotations, read-only, allow/deny."""

from __future__ import annotations

from arvancloud_mcp.guardrails import classify
from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


def test_classify():
    assert classify("arvan_list_servers") == "read"
    assert classify("arvan_get_server") == "read"
    assert classify("arvan_doctor") == "read"
    assert classify("arvan_security_generate_ssh_keypair") == "read"
    assert classify("arvan_create_server") == "write"
    assert classify("arvan_provision_server") == "write"
    assert classify("arvan_delete_server") == "destructive"
    assert classify("arvan_purge_cache") == "destructive"


async def test_annotations_are_set():
    mcp, _ = build_server(make_settings())
    tools = mcp._tool_manager._tools
    assert tools["arvan_list_servers"].annotations.readOnlyHint is True
    assert tools["arvan_delete_server"].annotations.destructiveHint is True
    assert tools["arvan_create_server"].annotations.readOnlyHint is False


async def test_read_only_mode_prunes_and_guards():
    mcp, _ = build_server(make_settings(read_only=True))
    names = {t.name for t in await mcp.list_tools()}
    assert "arvan_list_servers" in names
    assert "arvan_request" in names
    assert "arvan_delete_server" not in names
    assert "arvan_create_server" not in names

    out = unwrap(await mcp.call_tool("arvan_request", {"method": "POST", "path": "/x"}))
    assert out["ok"] is False
    assert "read-only" in out["error"]


async def test_deny_list():
    mcp, _ = build_server(make_settings(tools_deny=("arvan_delete_*",)))
    names = {t.name for t in await mcp.list_tools()}
    assert "arvan_delete_server" not in names
    assert "arvan_list_servers" in names


async def test_allow_list_keeps_only_matches_plus_essentials():
    mcp, _ = build_server(make_settings(tools_allow=("arvan_list_*",)))
    names = {t.name for t in await mcp.list_tools()}
    assert "arvan_list_servers" in names
    assert "arvan_create_server" not in names
    assert "arvan_request" in names
