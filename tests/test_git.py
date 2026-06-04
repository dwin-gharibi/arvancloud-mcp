"""Tests for the git tools (git binary mocked)."""

from __future__ import annotations

import arvancloud_mcp.tools.git as gitmod
from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


def _patch_run(monkeypatch):
    calls = []

    async def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "cwd": kw.get("cwd")})
        return {"installed": True, "ok": True, "stdout": "", "exit_code": 0}

    monkeypatch.setattr(gitmod, "run_command", fake_run)
    return calls


async def test_git_available():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_git_available", {}))
    assert "git" in out and "installed" in out["git"]


async def test_git_clone_returns_path(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool(
            "arvan_git_clone",
            {"repo_url": "https://example.com/repo.git", "dest": "/tmp/repo", "branch": "main"},
        )
    )
    assert out["path"] == "/tmp/repo"
    cmd = calls[-1]["cmd"]
    assert cmd[0:2] == ["git", "clone"]
    assert "--branch" in cmd and "main" in cmd
    assert cmd[-2:] == ["https://example.com/repo.git", "/tmp/repo"]


async def test_git_status_runs_in_directory(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_git_status", {"directory": "/work/repo"})
    assert calls[-1]["cwd"] == "/work/repo"
    assert calls[-1]["cmd"][0:2] == ["git", "status"]
