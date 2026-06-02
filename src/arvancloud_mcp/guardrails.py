"""Guardrails: classify tools, annotate them, and enforce read-only / allow-deny.

Applied once after all tools are registered. It tags every tool with MCP
annotations (``readOnlyHint`` / ``destructiveHint``) so clients can tell safe
calls from dangerous ones, and can prune the toolset for a read-only deployment
or an explicit allow/deny list.
"""

from __future__ import annotations

import fnmatch
from typing import Any

from mcp.types import ToolAnnotations

_DESTRUCTIVE = (
    "delete", "destroy", "purge", "rebuild", "remove", "detach", "reset",
    "rename", "resize", "uninstall",
)
_READ = (
    "list", "get", "describe", "status", "available", "capabilities", "doctor",
    "audit", "scan", "validate", "lint", "check", "lookup", "dns_lookup",
    "reverse_dns", "tls_cert", "http_check", "http_load_test", "port_scan",
    "my_public_ip", "metrics", "audit_log", "plan", "diff", "log", "wait",
    "generate_password", "generate_ssh_keypair", "options", "ptr_records",
    "ls_files", "list_files",
)
_ALWAYS_KEEP = {"arvan_request", "arvan_capabilities", "arvan_doctor"}


def classify(name: str) -> str:
    """Return ``read``, ``write`` or ``destructive`` for a tool name."""

    n = name.lower()
    if any(k in n for k in _READ):
        return "read"
    if any(k in n for k in _DESTRUCTIVE):
        return "destructive"
    return "write"


def _matches_any(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def apply_guardrails(mcp, settings) -> dict[str, Any]:
    """Annotate tools and prune them per settings. Returns a summary."""

    tools = mcp._tool_manager._tools
    counts = {"read": 0, "write": 0, "destructive": 0}
    removed: list[str] = []

    for name, tool in list(tools.items()):
        cls = classify(name)
        counts[cls] += 1
        tool.annotations = ToolAnnotations(
            readOnlyHint=(cls == "read"),
            destructiveHint=(cls == "destructive"),
            idempotentHint=(cls == "destructive"),
        )

    if settings.read_only:
        for name in list(tools):
            if name in _ALWAYS_KEEP:
                continue
            if classify(name) != "read":
                tools.pop(name, None)
                removed.append(name)

    if settings.tools_allow:
        for name in list(tools):
            if name in _ALWAYS_KEEP:
                continue
            if not _matches_any(name, settings.tools_allow):
                tools.pop(name, None)
                removed.append(name)

    if settings.tools_deny:
        for name in list(tools):
            if _matches_any(name, settings.tools_deny):
                tools.pop(name, None)
                removed.append(name)

    return {
        "read_only": settings.read_only,
        "counts": counts,
        "removed": sorted(set(removed)),
        "active_tools": len(tools),
    }
