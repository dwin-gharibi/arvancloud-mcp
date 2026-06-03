"""Background tasks & scheduling.

Submit any tool to run in the background, on a delay, or on a recurring
interval; poll its status/result; or be notified on completion via a webhook.

Scale notes:
* Concurrency is bounded by ``ARVAN_TASK_MAX_CONCURRENCY`` and the task history
  by ``ARVAN_TASK_MAX_TASKS`` (oldest finished tasks are evicted).
* State is in-process. For a single instance (stdio or one HTTP replica) that is
  all you need. Across many HTTP replicas, a task lives on the replica that
  accepted it — use the webhook announcement (``ARVAN_TASK_WEBHOOK`` or a
  per-task ``announce_webhook``) to get replica-independent completion signals,
  or run an external queue and submit through it.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx
from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient

_BLOCKED_PREFIXES = ("arvan_task_",)
_MAX_HISTORY_PER_TASK = 10
_MAX_ANNOUNCE_RESULT = 4000


@dataclass
class TaskRecord:
    id: str
    name: str
    tool: str
    arguments: dict
    delay: float
    interval: float | None
    max_runs: int | None
    announce_webhook: str | None
    status: str = "scheduled"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    runs: int = 0
    last_result: Any = None
    last_error: str | None = None
    history: list = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tool": self.tool,
            "status": self.status,
            "runs": self.runs,
            "interval": self.interval,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_error": self.last_error,
        }

    def detail(self) -> dict:
        d = self.summary()
        d["arguments"] = self.arguments
        d["last_result"] = self.last_result
        d["history"] = self.history
        d["max_runs"] = self.max_runs
        return d


Runner = Callable[[str, dict], Awaitable[Any]]


class TaskManager:
    """Runs and tracks background/scheduled tool invocations."""

    def __init__(
        self,
        runner: Runner,
        *,
        max_tasks: int = 1000,
        max_concurrency: int = 20,
        default_webhook: str | None = None,
    ) -> None:
        self._runner = runner
        self._records: "OrderedDict[str, TaskRecord]" = OrderedDict()
        self._aio: dict[str, asyncio.Task] = {}
        self._sem = asyncio.Semaphore(max_concurrency)
        self._max_tasks = max_tasks
        self._default_webhook = default_webhook

    def submit(
        self,
        tool: str,
        arguments: dict | None = None,
        *,
        delay: float = 0.0,
        interval: float | None = None,
        max_runs: int | None = None,
        name: str | None = None,
        announce_webhook: str | None = None,
    ) -> TaskRecord:
        if tool.startswith(_BLOCKED_PREFIXES):
            raise ValueError(f"tool '{tool}' cannot be scheduled as a background task")
        if interval is not None:
            interval = max(1.0, float(interval))
        delay = max(0.0, min(float(delay), 86400.0))
        record = TaskRecord(
            id=uuid.uuid4().hex[:12],
            name=name or tool,
            tool=tool,
            arguments=arguments or {},
            delay=delay,
            interval=interval,
            max_runs=max_runs if max_runs is not None else (None if interval else 1),
            announce_webhook=announce_webhook or self._default_webhook,
        )
        self._records[record.id] = record
        self._evict()
        self._aio[record.id] = asyncio.create_task(self._run(record))
        return record

    def list(self) -> list[dict]:
        return [r.summary() for r in reversed(self._records.values())]

    def get(self, task_id: str) -> TaskRecord | None:
        return self._records.get(task_id)

    def cancel(self, task_id: str) -> bool:
        record = self._records.get(task_id)
        if not record:
            return False
        task = self._aio.get(task_id)
        if task and not task.done():
            task.cancel()
            record.status = "cancelled"
            record.updated_at = time.time()
            return True
        return False

    async def aclose(self) -> None:
        for task in list(self._aio.values()):
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._aio.values(), return_exceptions=True)

    def _evict(self) -> None:
        while len(self._records) > self._max_tasks:
            for tid, rec in list(self._records.items()):
                if rec.status in ("succeeded", "failed", "cancelled"):
                    self._records.pop(tid, None)
                    self._aio.pop(tid, None)
                    break
            else:
                break

    async def _run(self, record: TaskRecord) -> None:
        try:
            if record.delay:
                record.status = "scheduled"
                await asyncio.sleep(record.delay)
            while True:
                if record.max_runs is not None and record.runs >= record.max_runs:
                    break
                await self._run_once(record)
                if record.interval is None:
                    break
                if record.max_runs is not None and record.runs >= record.max_runs:
                    break
                await asyncio.sleep(record.interval)
        except asyncio.CancelledError:
            record.status = "cancelled"
            record.updated_at = time.time()
            raise

    async def _run_once(self, record: TaskRecord) -> None:
        record.status = "running"
        record.updated_at = time.time()
        run_status = "succeeded"
        result: Any = None
        error: str | None = None
        async with self._sem:
            started = time.time()
            try:
                result = await self._runner(record.tool, record.arguments)
                record.last_result = result
                record.last_error = None
            except Exception as exc:
                run_status = "failed"
                error = f"{type(exc).__name__}: {exc}"
                record.last_error = error
        record.runs += 1
        record.status = run_status
        record.updated_at = time.time()
        record.history.append(
            {"run": record.runs, "status": run_status, "error": error,
             "duration_s": round(time.time() - started, 3)}
        )
        del record.history[:-_MAX_HISTORY_PER_TASK]
        await self._announce(record, run_status, result, error)

    async def _announce(
        self, record: TaskRecord, run_status: str, result: Any, error: str | None
    ) -> None:
        url = record.announce_webhook
        if not url:
            return
        try:
            result_str = json.dumps(result, default=str)
        except (TypeError, ValueError):
            result_str = str(result)
        if len(result_str) > _MAX_ANNOUNCE_RESULT:
            result_str = result_str[:_MAX_ANNOUNCE_RESULT] + "...[truncated]"
        payload = {
            "task_id": record.id,
            "name": record.name,
            "tool": record.tool,
            "status": run_status,
            "run": record.runs,
            "error": error,
            "result": result_str,
            "finished_at": record.updated_at,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as hc:
                await hc.post(url, json=payload)
        except httpx.HTTPError:
            pass


def _extract(result: Any) -> Any:
    """Turn a FastMCP call_tool return into a JSON-serialisable value."""

    def _maybe(value):
        if isinstance(value, dict) and set(value.keys()) == {"result"}:
            return value["result"]
        return value

    content = result
    if isinstance(result, tuple):
        if result[1] is not None:
            return _maybe(result[1])
        content = result[0]
    for block in content or []:
        text = getattr(block, "text", None)
        if text is not None:
            try:
                return _maybe(json.loads(text))
            except (ValueError, TypeError):
                return text
    return None


def register(mcp: FastMCP, client: ArvanClient) -> None:
    settings = client.settings

    async def _runner(tool: str, arguments: dict) -> Any:
        return _extract(await mcp.call_tool(tool, arguments or {}))

    manager = TaskManager(
        _runner,
        max_tasks=getattr(settings, "task_max_tasks", 1000),
        max_concurrency=getattr(settings, "task_max_concurrency", 20),
        default_webhook=getattr(settings, "task_webhook", "") or None,
    )
    mcp._arvan_task_manager = manager

    @mcp.tool()
    async def arvan_task_submit(
        tool: str,
        arguments: dict[str, Any] | None = None,
        delay_seconds: float = 0.0,
        interval_seconds: float | None = None,
        max_runs: int | None = None,
        name: str | None = None,
        announce_webhook: str | None = None,
    ) -> Any:
        """Run another tool in the background, now/later/recurring.

        Args:
            tool: Name of the tool to run (e.g. ``arvan_provision_server``,
                ``arvan_net_http_load_test``, ``arvan_security_scan_vulnerabilities``).
            arguments: Arguments for that tool.
            delay_seconds: Wait this long before the first run.
            interval_seconds: If set, re-run every N seconds (min 1) — a schedule.
            max_runs: Stop after this many runs (default 1; unlimited when an
                interval is set and this is omitted — cancel to stop).
            name: Friendly label for the task.
            announce_webhook: POST a status payload here when each run finishes
                (falls back to ARVAN_TASK_WEBHOOK). Use this for completion
                notifications that work even across replicas / after disconnect.

        Returns the task record (with its id) immediately; poll with
        ``arvan_task_status`` or wait for the webhook.
        """

        try:
            record = manager.submit(
                tool,
                arguments,
                delay=delay_seconds,
                interval=interval_seconds,
                max_runs=max_runs,
                name=name,
                announce_webhook=announce_webhook,
            )
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, **record.summary()}

    @mcp.tool()
    async def arvan_task_list() -> Any:
        """List background tasks and their status (most recent first)."""

        return {"tasks": manager.list()}

    @mcp.tool()
    async def arvan_task_status(task_id: str) -> Any:
        """Get a background task's full status, last result, and run history."""

        record = manager.get(task_id)
        if not record:
            return {"ok": False, "error": f"no task '{task_id}'"}
        return record.detail()

    @mcp.tool()
    async def arvan_task_cancel(task_id: str) -> Any:
        """Cancel a scheduled/running background task."""

        ok = manager.cancel(task_id)
        return {"ok": ok, "task_id": task_id}
