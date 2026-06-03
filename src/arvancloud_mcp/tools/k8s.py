"""Kubernetes & Helm tools — deploy workloads to any cluster (incl. ArvanCloud PaaS).

Wraps ``kubectl`` and ``helm``. Provide a kubeconfig either inline
(``kubeconfig`` string) or via a path (``kubeconfig_path``); ArvanCloud PaaS
issues one with ``arvan paas`` / the panel. These let the MCP provision and
manage Kubernetes resources — including deploying this very server from
``deploy/kubernetes``.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from typing import Any, Iterator

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._exec import run_command, which


@contextmanager
def _kubeconfig_env(
    kubeconfig: str | None, kubeconfig_path: str | None
) -> Iterator[dict[str, str]]:
    """Yield env vars pointing KUBECONFIG at an inline or on-disk config."""

    if kubeconfig:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".kubeconfig", delete=True
        ) as fh:
            fh.write(kubeconfig)
            fh.flush()
            yield {"KUBECONFIG": fh.name}
    elif kubeconfig_path:
        yield {"KUBECONFIG": kubeconfig_path}
    else:
        yield {}


@contextmanager
def _manifest_file(
    manifest: str | None, directory: str | None
) -> Iterator[str]:
    if directory:
        yield directory
        return
    if not manifest:
        raise ValueError("Provide either 'manifest' (YAML) or 'directory'.")
    with tempfile.TemporaryDirectory(prefix="arvan-k8s-") as tmp:
        path = os.path.join(tmp, "manifest.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(manifest)
        yield path


def register(mcp: FastMCP, client: ArvanClient) -> None:
    timeout = getattr(client.settings, "iac_timeout", 120.0)

    @mcp.tool()
    async def arvan_k8s_available_tools() -> Any:
        """Report whether kubectl and helm are installed."""

        return {
            "kubectl": {"installed": which("kubectl") is not None, "path": which("kubectl")},
            "helm": {"installed": which("helm") is not None, "path": which("helm")},
        }

    @mcp.tool()
    async def arvan_kubectl(
        args: list[str],
        kubeconfig: str | None = None,
        kubeconfig_path: str | None = None,
        namespace: str | None = None,
    ) -> Any:
        """Run an arbitrary kubectl command (e.g. ``["get","pods","-o","wide"]``)."""

        cmd = ["kubectl"]
        if namespace:
            cmd += ["-n", namespace]
        cmd += list(args)
        with _kubeconfig_env(kubeconfig, kubeconfig_path) as env:
            return await run_command(cmd, timeout=timeout, env_extra=env)

    @mcp.tool()
    async def arvan_k8s_apply(
        manifest: str | None = None,
        directory: str | None = None,
        kubeconfig: str | None = None,
        kubeconfig_path: str | None = None,
        namespace: str | None = None,
    ) -> Any:
        """``kubectl apply`` a manifest (inline YAML) or a directory of manifests."""

        with _kubeconfig_env(kubeconfig, kubeconfig_path) as env:
            with _manifest_file(manifest, directory) as path:
                cmd = ["kubectl", "apply", "-f", path]
                if namespace:
                    cmd += ["-n", namespace]
                return await run_command(cmd, timeout=timeout, env_extra=env)

    @mcp.tool()
    async def arvan_k8s_delete(
        manifest: str | None = None,
        directory: str | None = None,
        kubeconfig: str | None = None,
        kubeconfig_path: str | None = None,
        namespace: str | None = None,
    ) -> Any:
        """``kubectl delete -f`` a manifest or directory."""

        with _kubeconfig_env(kubeconfig, kubeconfig_path) as env:
            with _manifest_file(manifest, directory) as path:
                cmd = ["kubectl", "delete", "-f", path]
                if namespace:
                    cmd += ["-n", namespace]
                return await run_command(cmd, timeout=timeout, env_extra=env)

    @mcp.tool()
    async def arvan_k8s_get(
        resource: str,
        name: str | None = None,
        namespace: str | None = None,
        kubeconfig: str | None = None,
        kubeconfig_path: str | None = None,
        output: str = "json",
    ) -> Any:
        """``kubectl get`` resources (e.g. resource='pods'), default JSON output."""

        cmd = ["kubectl", "get", resource]
        if name:
            cmd.append(name)
        if namespace:
            cmd += ["-n", namespace]
        cmd += ["-o", output]
        with _kubeconfig_env(kubeconfig, kubeconfig_path) as env:
            return await run_command(cmd, timeout=timeout, env_extra=env)

    @mcp.tool()
    async def arvan_helm_install(
        release: str,
        chart: str,
        namespace: str | None = None,
        values: dict[str, Any] | None = None,
        kubeconfig: str | None = None,
        kubeconfig_path: str | None = None,
        create_namespace: bool = True,
        upgrade: bool = True,
    ) -> Any:
        """Install/upgrade a Helm chart.

        ``values`` are passed as ``--set key=value`` pairs (flat keys). ``chart``
        may be a local path (e.g. ``deploy/helm/arvancloud-mcp``) or a repo chart.
        """

        verb = ["upgrade", "--install"] if upgrade else ["install"]
        cmd = ["helm", *verb, release, chart]
        if namespace:
            cmd += ["-n", namespace]
            if create_namespace:
                cmd.append("--create-namespace")
        for key, value in (values or {}).items():
            cmd += ["--set", f"{key}={value}"]
        with _kubeconfig_env(kubeconfig, kubeconfig_path) as env:
            return await run_command(cmd, timeout=max(timeout, 300.0), env_extra=env)

    @mcp.tool()
    async def arvan_helm_uninstall(
        release: str,
        namespace: str | None = None,
        kubeconfig: str | None = None,
        kubeconfig_path: str | None = None,
    ) -> Any:
        """Uninstall a Helm release."""

        cmd = ["helm", "uninstall", release]
        if namespace:
            cmd += ["-n", namespace]
        with _kubeconfig_env(kubeconfig, kubeconfig_path) as env:
            return await run_command(cmd, timeout=timeout, env_extra=env)
