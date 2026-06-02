"""Shared subprocess helpers for tools that shell out to external binaries."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Iterator, Sequence

_MAX_OUTPUT = 60_000


@contextmanager
def workspace(
    files: dict[str, str] | None, directory: str | None
) -> Iterator[str]:
    """Yield a working directory: an existing path, or a temp dir of ``files``.

    ``files`` maps relative paths to contents; each is written into a temporary
    directory that is cleaned up on exit. Paths are validated to prevent escaping
    the workspace.
    """

    if directory:
        yield directory
        return
    if not files:
        raise ValueError("Provide either 'files' (path->content) or 'directory'.")
    with tempfile.TemporaryDirectory(prefix="arvan-ws-") as tmp:
        for rel, content in files.items():
            if os.path.isabs(rel) or ".." in rel.split("/"):
                raise ValueError(f"Unsafe file path: {rel!r}")
            dest = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dest) or tmp, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(content)
        yield tmp


def which(binary: str) -> str | None:
    """Return the resolved path to ``binary`` if it is on PATH, else None."""

    return shutil.which(binary)


def _truncate(text: str) -> str:
    if len(text) > _MAX_OUTPUT:
        return text[:_MAX_OUTPUT] + "\n... [truncated]"
    return text


async def run_command(
    cmd: Sequence[str],
    *,
    cwd: str | None = None,
    input_text: str | None = None,
    timeout: float = 120.0,
    env_extra: dict[str, str] | None = None,
) -> dict:
    """Run a command and capture its output.

    Returns ``{installed, command, exit_code, stdout, stderr, timed_out, ok}``.
    Never raises for a non-zero exit or a missing binary — callers inspect the
    returned dict.
    """

    binary = cmd[0]
    if which(binary) is None:
        return {
            "installed": False,
            "command": list(cmd),
            "error": f"'{binary}' is not installed or not on PATH.",
            "ok": False,
        }

    env = None
    if env_extra:
        env = {**os.environ, **env_extra}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.PIPE if input_text is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        return {
            "installed": True,
            "command": list(cmd),
            "error": f"failed to start '{binary}': {exc}",
            "ok": False,
        }

    stdin_bytes = input_text.encode("utf-8") if input_text is not None else None
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(input=stdin_bytes), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {
            "installed": True,
            "command": list(cmd),
            "timed_out": True,
            "ok": False,
            "error": f"command timed out after {timeout}s",
        }

    exit_code = proc.returncode
    return {
        "installed": True,
        "command": list(cmd),
        "exit_code": exit_code,
        "stdout": _truncate(stdout_b.decode("utf-8", "replace")),
        "stderr": _truncate(stderr_b.decode("utf-8", "replace")),
        "timed_out": False,
        "ok": exit_code == 0,
    }


def version_of(binary: str, version_arg: str = "--version") -> dict:
    """Synchronously probe a binary's presence (used by capability listings)."""

    path = which(binary)
    return {"installed": path is not None, "path": path}
