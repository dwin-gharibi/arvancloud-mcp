"""Tests for the SSH remote-exec tools (asyncssh mocked)."""

from __future__ import annotations

import asyncssh
import pytest

from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


class _FakeResult:
    def __init__(self, exit_status=0, stdout="", stderr=""):
        self.exit_status = exit_status
        self.stdout = stdout
        self.stderr = stderr


class _FakeSftpFile:
    def __init__(self, store, path, mode):
        self._store, self._path, self._mode = store, path, mode

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def write(self, data):
        self._store[self._path] = data

    async def read(self, n=-1):
        return self._store.get(self._path, b"")


class _FakeSftp:
    def __init__(self, store):
        self._store = store

    def open(self, path, mode):
        return _FakeSftpFile(self._store, path, mode)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, store):
        self.run_calls: list[dict] = []
        self.closed = False
        self._store = store

    async def run(self, command, check=False, timeout=None, input=None):
        self.run_calls.append({"command": command, "input": input, "timeout": timeout})
        return _FakeResult(0, f"ran:{command}", "")

    def close(self):
        self.closed = True

    def get_extra_info(self, key):
        return "SSH-2.0-OpenSSH_9.0" if key == "server_version" else None

    def start_sftp_client(self):
        return _FakeSftp(self._store)


@pytest.fixture
def ssh_server(monkeypatch):
    captured: dict = {}
    store: dict = {}
    conn = _FakeConn(store)

    async def fake_connect(**kwargs):
        captured.update(kwargs)
        return conn

    monkeypatch.setattr(asyncssh, "connect", fake_connect)
    mcp, _client = build_server(make_settings())
    return mcp, captured, conn, store


async def test_ssh_run_returns_output_and_uses_defaults(ssh_server):
    mcp, captured, conn, _store = ssh_server
    out = unwrap(
        await mcp.call_tool(
            "arvan_ssh_run", {"host": "1.2.3.4", "command": "uname -a"}
        )
    )
    assert out["exit_status"] == 0
    assert out["stdout"] == "ran:uname -a"
    assert captured["host"] == "1.2.3.4"
    assert captured["port"] == 22
    assert captured["username"] == "root"
    assert captured["known_hosts"] is None
    assert conn.closed is True


async def test_ssh_run_honours_overrides(ssh_server):
    mcp, captured, _conn, _store = ssh_server
    await mcp.call_tool(
        "arvan_ssh_run",
        {
            "host": "10.0.0.5",
            "command": "id",
            "username": "ubuntu",
            "port": 2222,
            "password": "secret",
        },
    )
    assert captured["username"] == "ubuntu"
    assert captured["port"] == 2222
    assert captured["password"] == "secret"


async def test_ssh_run_script_pipes_to_interpreter(ssh_server):
    mcp, _captured, conn, _store = ssh_server
    await mcp.call_tool(
        "arvan_ssh_run_script",
        {"host": "1.2.3.4", "script": "echo hi\necho bye"},
    )
    last = conn.run_calls[-1]
    assert last["command"] == "bash -s"
    assert last["input"] == "echo hi\necho bye"


async def test_ssh_upload_and_download_roundtrip(ssh_server):
    mcp, _captured, _conn, store = ssh_server
    await mcp.call_tool(
        "arvan_ssh_upload_file",
        {"host": "1.2.3.4", "remote_path": "/tmp/x.txt", "content": "payload"},
    )
    assert store["/tmp/x.txt"] == b"payload"

    out = unwrap(
        await mcp.call_tool(
            "arvan_ssh_download_file",
            {"host": "1.2.3.4", "remote_path": "/tmp/x.txt"},
        )
    )
    assert out["content"] == "payload"


async def test_ssh_check_connection(ssh_server):
    mcp, _captured, _conn, _store = ssh_server
    out = unwrap(
        await mcp.call_tool("arvan_ssh_check_connection", {"host": "1.2.3.4"})
    )
    assert out["connected"] is True
    assert "OpenSSH" in out["server_version"]
