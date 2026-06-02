"""Tool modules for the ArvanCloud MCP server.

Each module exposes a ``register(mcp, client)`` function that attaches its
tools to the given :class:`~mcp.server.fastmcp.FastMCP` instance. The
:func:`register_all` helper wires up every service that is enabled in the
client's settings.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ..config import ALWAYS_ON
from . import (
    cdn,
    common,
    compute,
    dns,
    docs,
    git,
    iac,
    k8s,
    live,
    net,
    network,
    notify,
    objectstorage,
    observability,
    provision,
    security,
    ssh,
    storage,
    tasks,
    vod,
)

_MODULES = {
    "common": common,
    "compute": compute,
    "network": network,
    "storage": storage,
    "objectstorage": objectstorage,
    "cdn": cdn,
    "dns": dns,
    "vod": vod,
    "live": live,
    "ssh": ssh,
    "provision": provision,
    "k8s": k8s,
    "net": net,
    "iac": iac,
    "security": security,
    "git": git,
    "tasks": tasks,
    "notify": notify,
    "observability": observability,
    "docs": docs,
}


def register_all(mcp: FastMCP, client: ArvanClient) -> list[str]:
    """Register every enabled service module. Returns the list registered."""

    registered: list[str] = []
    for name, module in _MODULES.items():
        if name in ALWAYS_ON or client.settings.is_enabled(name):
            module.register(mcp, client)
            registered.append(name)
    return registered


__all__ = ["register_all"]
