"""Tests for the Kubernetes / Helm tools (kubectl/helm mocked)."""

from __future__ import annotations

import arvancloud_mcp.tools.k8s as k8smod
from arvancloud_mcp.server import build_server

from .conftest import make_settings, unwrap


def _patch_run(monkeypatch):
    calls = []

    async def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "env": kw.get("env_extra")})
        return {"installed": True, "ok": True, "stdout": "ok", "exit_code": 0}

    monkeypatch.setattr(k8smod, "run_command", fake_run)
    return calls


async def test_available_tools():
    mcp, _ = build_server(make_settings())
    out = unwrap(await mcp.call_tool("arvan_k8s_available_tools", {}))
    assert "kubectl" in out and "helm" in out


async def test_kubectl_passthrough(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_kubectl", {"args": ["get", "pods"], "namespace": "default"}
    )
    cmd = calls[-1]["cmd"]
    assert cmd[0] == "kubectl"
    assert "get" in cmd and "pods" in cmd
    assert cmd[1:3] == ["-n", "default"]


async def test_apply_inline_manifest_sets_kubeconfig(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_k8s_apply",
        {"manifest": "apiVersion: v1\nkind: Namespace\nmetadata:\n  name: x\n",
         "kubeconfig": "fake-kubeconfig-content"},
    )
    call = calls[-1]
    assert call["cmd"][0:2] == ["kubectl", "apply"]
    assert "-f" in call["cmd"]
    assert "KUBECONFIG" in call["env"]


async def test_helm_install_sets_values(monkeypatch):
    calls = _patch_run(monkeypatch)
    mcp, _ = build_server(make_settings())
    await mcp.call_tool(
        "arvan_helm_install",
        {
            "release": "mcp",
            "chart": "deploy/helm/arvancloud-mcp",
            "namespace": "mcp",
            "values": {"image.tag": "v1"},
        },
    )
    cmd = calls[-1]["cmd"]
    assert cmd[0] == "helm"
    assert "upgrade" in cmd and "--install" in cmd
    assert "--set" in cmd and "image.tag=v1" in cmd
    assert "--create-namespace" in cmd
