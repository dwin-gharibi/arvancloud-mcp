"""Tests for the one-call provisioning tool (API + SSH mocked)."""

from __future__ import annotations

import json

import asyncssh
import httpx
import respx

import arvancloud_mcp.tools.provision as provmod
from arvancloud_mcp.server import build_server

from .conftest import TEST_BASE_URL, make_settings, unwrap


class _Result:
    exit_status = 0
    stdout = "installed nginx"
    stderr = ""


class _Conn:
    async def run(self, *args, **kwargs):
        return _Result()

    def close(self):
        pass


def _mock_lifecycle(mock):
    mock.post("/ecc/v1/regions/ir-thr-c2/ssh-keys").mock(
        return_value=httpx.Response(201, json={"data": {"name": "k"}})
    )
    mock.post("/ecc/v1/regions/ir-thr-c2/servers").mock(
        return_value=httpx.Response(201, json={"data": {"id": "s1"}})
    )
    mock.get("/ecc/v1/regions/ir-thr-c2/servers/s1").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"id": "s1", "status": "ACTIVE", "addresses": ["1.2.3.4"]}},
        )
    )


async def test_provision_full_flow(monkeypatch):
    async def fake_wait(host, port, timeout):
        return True

    async def fake_connect(**kwargs):
        return _Conn()

    monkeypatch.setattr(provmod, "_wait_tcp", fake_wait)
    monkeypatch.setattr(asyncssh, "connect", fake_connect)

    mcp, _ = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        _mock_lifecycle(mock)
        out = unwrap(
            await mcp.call_tool(
                "arvan_provision_server",
                {
                    "name": "web1",
                    "flavor_id": "g1-1-1-0",
                    "image_id": "ubuntu-22",
                    "packages": ["nginx"],
                    "wait_timeout": 30,
                },
            )
        )

    assert out["server_id"] == "s1"
    assert out["public_ip"] == "1.2.3.4"
    assert out["install"]["ok"] is True
    assert "ssh_private_key" in out


async def test_provision_passes_init_script(monkeypatch):
    mcp, _ = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        servers = mock.post("/ecc/v1/regions/ir-thr-c2/servers").mock(
            return_value=httpx.Response(201, json={"data": {"id": "s1"}})
        )
        mock.get("/ecc/v1/regions/ir-thr-c2/servers/s1").mock(
            return_value=httpx.Response(
                200, json={"data": {"id": "s1", "status": "ACTIVE"}}
            )
        )
        await mcp.call_tool(
            "arvan_provision_server",
            {
                "name": "web1",
                "flavor_id": "g1-1-1-0",
                "image_id": "ubuntu-22",
                "generate_ssh_key": False,
                "init_script": "echo hello",
                "wait_timeout": 30,
            },
        )
    body = json.loads(servers.calls.last.request.content)
    assert body["init_script"] == "echo hello"


async def test_ansible_playbook_command(monkeypatch):
    calls = []

    async def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "env": kw.get("env_extra")})
        return {"installed": True, "ok": True, "stdout": ""}

    monkeypatch.setattr(provmod, "run_command", fake_run)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_ansible_playbook",
        {"host": "1.2.3.4", "playbook": "- hosts: all\n  tasks: []\n"},
    )
    assert calls[-1]["cmd"][0] == "ansible-playbook"
    assert calls[-1]["env"]["ANSIBLE_HOST_KEY_CHECKING"] == "False"
