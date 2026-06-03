"""Observability & ops: tool-call metrics, an audit log, and rate limiting.

Wraps the tool-call path so every invocation is counted (with latency and
errors), mutating calls are recorded in an audit ring buffer, and an optional
per-minute rate limit can shed load. Exposed via ``arvan_metrics`` (JSON +
Prometheus text) and ``arvan_audit_log``.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ..guardrails import classify


class _Metrics:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.calls: dict[str, int] = {}
        self.errors: dict[str, int] = {}
        self.latency_ms: dict[str, float] = {}

    def record(self, name: str, dt_ms: float, ok: bool) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1
        self.latency_ms[name] = self.latency_ms.get(name, 0.0) + dt_ms
        if not ok:
            self.errors[name] = self.errors.get(name, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        total = sum(self.calls.values())
        errs = sum(self.errors.values())
        per_tool = {
            name: {
                "calls": c,
                "errors": self.errors.get(name, 0),
                "avg_ms": round(self.latency_ms.get(name, 0.0) / c, 2) if c else 0.0,
            }
            for name, c in sorted(self.calls.items(), key=lambda kv: -kv[1])
        }
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "total_calls": total,
            "total_errors": errs,
            "tools": per_tool,
        }

    def prometheus(self) -> str:
        lines = [
            "# HELP arvan_mcp_tool_calls_total Tool calls.",
            "# TYPE arvan_mcp_tool_calls_total counter",
        ]
        for name, c in self.calls.items():
            lines.append(f'arvan_mcp_tool_calls_total{{tool="{name}"}} {c}')
        lines += [
            "# HELP arvan_mcp_tool_errors_total Tool errors.",
            "# TYPE arvan_mcp_tool_errors_total counter",
        ]
        for name, c in self.errors.items():
            lines.append(f'arvan_mcp_tool_errors_total{{tool="{name}"}} {c}')
        return "\n".join(lines) + "\n"


def register(mcp: FastMCP, client: ArvanClient) -> None:
    settings = client.settings
    metrics = _Metrics()
    audit: deque[dict] = deque(maxlen=1000)
    rate_window: deque[float] = deque()
    limit = max(0, int(getattr(settings, "rate_limit_per_min", 0) or 0))

    tm = mcp._tool_manager
    original_call = tm.call_tool

    async def wrapped_call(name, arguments, *args, **kwargs):
        now = time.monotonic()
        if limit:
            while rate_window and now - rate_window[0] > 60.0:
                rate_window.popleft()
            if len(rate_window) >= limit:
                raise RuntimeError(
                    f"rate limit exceeded ({limit}/min); try again shortly"
                )
            rate_window.append(now)

        start = time.perf_counter()
        ok = True
        try:
            return await original_call(name, arguments, *args, **kwargs)
        except Exception:
            ok = False
            raise
        finally:
            dt_ms = (time.perf_counter() - start) * 1000
            metrics.record(name, dt_ms, ok)
            if classify(name) != "read":
                audit.append(
                    {
                        "ts": time.time(),
                        "tool": name,
                        "ok": ok,
                        "args": sorted((arguments or {}).keys()),
                    }
                )

    tm.call_tool = wrapped_call

    @mcp.tool()
    async def arvan_metrics(prometheus: bool = False) -> Any:
        """Return server tool-call metrics (calls, errors, latency).

        Set ``prometheus=True`` for Prometheus text-exposition format.
        """

        if prometheus:
            return metrics.prometheus()
        snap = metrics.snapshot()
        snap["rate_limit_per_min"] = limit or None
        return snap

    @mcp.tool()
    async def arvan_audit_log(limit_entries: int = 100) -> Any:
        """Return the most recent mutating tool calls (newest last)."""

        n = max(1, min(limit_entries, len(audit) or 1))
        return {"entries": list(audit)[-n:], "total_recorded": len(audit)}
