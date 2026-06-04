"""Tests for the security & hardening tools."""

from __future__ import annotations

import httpx
import respx

import arvancloud_mcp.tools.security as secmod
from arvancloud_mcp.server import build_server

from .conftest import TEST_BASE_URL, make_settings, unwrap


async def test_generate_password():
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool("arvan_security_generate_password", {"length": 20})
    )
    pw = out["password"]
    assert len(pw) == 20
    assert any(c.islower() for c in pw)
    assert any(c.isupper() for c in pw)
    assert any(c.isdigit() for c in pw)


async def test_generate_ssh_keypair_ed25519():
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool("arvan_security_generate_ssh_keypair", {"comment": "demo"})
    )
    assert out["key_type"] == "ed25519"
    assert out["public_key"].startswith("ssh-ed25519 ")
    assert out["public_key"].endswith(" demo")
    assert "OPENSSH PRIVATE KEY" in out["private_key"]


async def test_generate_ssh_keypair_rsa():
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool(
            "arvan_security_generate_ssh_keypair", {"key_type": "rsa", "bits": 2048}
        )
    )
    assert out["key_type"] == "rsa"
    assert out["public_key"].startswith("ssh-rsa ")


async def test_http_headers_grading():
    mcp, _ = build_server(make_settings())
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://site.test/").mock(
            return_value=httpx.Response(
                200,
                headers={
                    "strict-transport-security": "max-age=63072000",
                    "content-security-policy": "default-src 'self'",
                    "x-content-type-options": "nosniff",
                    "server": "nginx",
                },
            )
        )
        out = unwrap(
            await mcp.call_tool("arvan_security_http_headers", {"url": "https://site.test/"})
        )
    assert "strict-transport-security" in out["present"]
    assert "Referrer-Policy" in out["missing"]
    assert out["grade"] != "F"
    assert out["discloses_server"] == "nginx"


async def test_audit_security_groups_flags_world_open_ssh():
    mcp, _ = build_server(make_settings())
    payload = {
        "data": [
            {
                "name": "open-sg",
                "rules": [
                    {"direction": "ingress", "ip": "0.0.0.0/0", "port_start": 22, "port_end": 22, "protocol": "tcp"},
                ],
            },
            {
                "name": "safe-sg",
                "rules": [
                    {"direction": "ingress", "ip": "10.0.0.0/8", "port_start": 22, "port_end": 22, "protocol": "tcp"},
                ],
            },
        ]
    }
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/ecc/v1/regions/ir-thr-c2/securities").mock(
            return_value=httpx.Response(200, json=payload)
        )
        out = unwrap(
            await mcp.call_tool("arvan_security_audit_security_groups", {})
        )
    assert out["ok"] is False
    assert len(out["findings"]) == 1
    finding = out["findings"][0]
    assert finding["security_group"] == "open-sg"
    assert finding["severity"] == "high"
    assert "SSH" in finding["issue"]


async def test_audit_security_groups_all_clear():
    mcp, _ = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/ecc/v1/regions/ir-thr-c2/securities").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        out = unwrap(await mcp.call_tool("arvan_security_audit_security_groups", {}))
    assert out["ok"] is True
    assert out["findings"] == []


async def test_scan_secrets_builds_gitleaks_command(monkeypatch):
    calls = []

    async def fake_run(cmd, **kw):
        calls.append(list(cmd))
        return {"installed": True, "ok": True, "stdout": "[]"}

    monkeypatch.setattr(secmod, "run_command", fake_run)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_security_scan_secrets", {"files": {"app.py": "secret=1"}}
    )
    assert calls[-1][0] == "gitleaks"


async def test_grype_image(monkeypatch):
    calls = []

    async def fake_run(cmd, **kw):
        calls.append(list(cmd))
        return {"installed": True, "ok": True, "stdout": "{}"}

    monkeypatch.setattr(secmod, "run_command", fake_run)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_security_grype", {"image": "nginx:latest"})
    assert calls[-1][0] == "grype"
    assert "nginx:latest" in calls[-1]


async def test_available_tools():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_security_available_tools", {}))
    assert "trivy" in out and "installed" in out["trivy"]
