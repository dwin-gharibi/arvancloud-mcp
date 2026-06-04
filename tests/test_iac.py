"""Tests for the IaC validation tools (external binaries mocked)."""

from __future__ import annotations

import os

import arvancloud_mcp.tools.iac as iacmod
from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


def _patch_run(monkeypatch, stdout="{}"):
    calls = []

    async def fake_run(cmd, **kw):
        cwd = kw.get("cwd")
        calls.append(
            {
                "cmd": list(cmd),
                "cwd": cwd,
                "has_main": bool(cwd) and os.path.exists(os.path.join(cwd, "main.tf")),
                "input": kw.get("input_text"),
                "env": kw.get("env_extra"),
            }
        )
        return {"installed": True, "ok": True, "exit_code": 0, "stdout": stdout}

    monkeypatch.setattr(iacmod, "run_command", fake_run)
    return calls


async def test_available_tools_returns_mapping():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_iac_available_tools", {}))
    assert "terraform" in out and "installed" in out["terraform"]


async def test_terraform_validate_materialises_files(monkeypatch):
    calls = _patch_run(monkeypatch, stdout='{"valid": true}')
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool(
            "arvan_iac_terraform_validate",
            {"files": {"main.tf": 'resource "null_resource" "x" {}'}, "init": False},
        )
    )
    assert out["validate"]["ok"] is True
    assert out["validate"]["parsed"] == {"valid": True}
    assert calls[-1]["cmd"][:2] == ["terraform", "validate"]
    assert calls[-1]["has_main"] is True


async def test_lint_dockerfile_passes_stdin(monkeypatch):
    calls = _patch_run(monkeypatch, stdout="[]")
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_iac_lint_dockerfile", {"content": "FROM scratch\n"}
    )
    assert calls[-1]["cmd"][0] == "hadolint"
    assert calls[-1]["input"] == "FROM scratch\n"


async def test_checkov_command(monkeypatch):
    calls = _patch_run(monkeypatch, stdout="{}")
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_iac_checkov", {"files": {"main.tf": "x"}, "framework": "terraform"}
    )
    assert calls[-1]["cmd"][0] == "checkov"
    assert "--framework" in calls[-1]["cmd"]


async def test_terraform_apply_refuses_without_approval(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    out = unwrap(
        await mcp.call_tool(
            "arvan_iac_terraform_apply", {"files": {"main.tf": "x"}}
        )
    )
    assert out["refused"] is True
    assert calls == []


async def test_terraform_apply_injects_api_key_env(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings(api_key="Apikey secret"))
    await mcp.call_tool(
        "arvan_iac_terraform_apply",
        {"files": {"main.tf": "x"}, "auto_approve": True, "init": False},
    )
    apply_call = [c for c in calls if c["cmd"][:2] == ["terraform", "apply"]][0]
    assert apply_call["env"]["TF_VAR_api_key"] == "Apikey secret"


async def test_terraform_cost_command(monkeypatch):
    calls = _patch_run(monkeypatch, stdout="{}")
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_iac_terraform_cost", {"files": {"main.tf": "x"}})
    assert calls[-1]["cmd"][0] == "infracost"


async def test_packer_validate_command(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_iac_packer_validate", {"files": {"x.pkr.hcl": "y"}})
    assert calls[-1]["cmd"][0] == "packer"


async def test_opentofu_validate_command(monkeypatch):
    calls = _patch_run(monkeypatch, stdout='{"valid": true}')
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_iac_opentofu_validate", {"files": {"main.tf": "x"}, "init": False}
    )
    assert calls[-1]["cmd"][:2] == ["tofu", "validate"]


async def test_tfsec_command(monkeypatch):
    calls = _patch_run(monkeypatch, stdout="{}")
    mcp, _ = build_server(make_settings())
    await mcp.call_tool("arvan_iac_tfsec", {"files": {"main.tf": "x"}})
    assert calls[-1]["cmd"][0] == "tfsec"
