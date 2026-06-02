"""Git tools — clone and inspect repositories (e.g. to validate/deploy IaC).

Pairs naturally with the IaC and Kubernetes tools: clone a repo, then run
``arvan_iac_terraform_plan`` / ``arvan_k8s_apply`` against its directory. Wraps
the ``git`` binary and degrades gracefully when it is absent.
"""

from __future__ import annotations

import tempfile
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._exec import run_command, which


def register(mcp: FastMCP, client: ArvanClient) -> None:
    timeout = getattr(client.settings, "iac_timeout", 120.0)

    @mcp.tool()
    async def arvan_git_available() -> Any:
        """Report whether the git binary is installed."""

        return {"git": {"installed": which("git") is not None, "path": which("git")}}

    @mcp.tool()
    async def arvan_git_clone(
        repo_url: str,
        dest: str | None = None,
        branch: str | None = None,
        depth: int = 1,
    ) -> Any:
        """Clone a repository to ``dest`` (defaults to a fresh temp directory).

        Returns the checkout path so you can pass it as ``directory`` to the IaC
        or Kubernetes tools. The path persists for the session.
        """

        if not dest:
            dest = tempfile.mkdtemp(prefix="arvan-git-")
        cmd = ["git", "clone"]
        if depth and depth > 0:
            cmd += ["--depth", str(depth)]
        if branch:
            cmd += ["--branch", branch]
        cmd += [repo_url, dest]
        result = await run_command(cmd, timeout=max(timeout, 300.0))
        result["path"] = dest
        return result

    @mcp.tool()
    async def arvan_git_status(directory: str) -> Any:
        """Show the working-tree status of a checkout (porcelain)."""

        return await run_command(
            ["git", "status", "--porcelain=v1", "--branch"], cwd=directory, timeout=timeout
        )

    @mcp.tool()
    async def arvan_git_log(directory: str, max_count: int = 10) -> Any:
        """Show recent commits (one line each)."""

        return await run_command(
            ["git", "log", f"-{max(1, min(max_count, 100))}", "--oneline", "--decorate"],
            cwd=directory,
            timeout=timeout,
        )

    @mcp.tool()
    async def arvan_git_diff(directory: str, staged: bool = False) -> Any:
        """Show the diff of unstaged (or, with ``staged``, staged) changes."""

        cmd = ["git", "diff", "--no-color"]
        if staged:
            cmd.append("--cached")
        return await run_command(cmd, cwd=directory, timeout=timeout)

    @mcp.tool()
    async def arvan_git_checkout(directory: str, ref: str) -> Any:
        """Check out a branch, tag, or commit."""

        return await run_command(
            ["git", "checkout", ref], cwd=directory, timeout=timeout
        )

    @mcp.tool()
    async def arvan_git_pull(directory: str) -> Any:
        """Pull the latest changes for the current branch."""

        return await run_command(["git", "pull", "--ff-only"], cwd=directory, timeout=timeout)

    @mcp.tool()
    async def arvan_git_list_files(directory: str) -> Any:
        """List tracked files in a checkout."""

        return await run_command(["git", "ls-files"], cwd=directory, timeout=timeout)
