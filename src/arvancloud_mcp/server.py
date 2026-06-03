"""Assembles and runs the ArvanCloud MCP server."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from . import __version__
from .client import ArvanClient
from .config import Settings
from .guardrails import apply_guardrails
from .tools import register_all

logger = logging.getLogger("arvancloud_mcp")

INSTRUCTIONS = """\
This server exposes the whole ArvanCloud platform: Cloud Server/IaaS, networking,
block & Object Storage (S3), CDN, Cloud DNS, Video on Demand, Live Streaming, and
direct SSH into your servers.

Getting started:
- Call `arvan_capabilities` to see every product and its endpoints.
- Most IaaS tools take an optional `region` (e.g. `ir-thr-c2`); set
  ARVAN_DEFAULT_REGION to avoid repeating it. `arvan_list_regions` lists them.
- For any endpoint without a dedicated tool, use `arvan_request` with a method
  and path (paths are listed by `arvan_capabilities`).

End-to-end example (provision -> configure):
1. `arvan_list_plans` / `arvan_list_images` to choose a flavor and image.
2. `arvan_create_ssh_key` (or reuse one) and `arvan_create_server(..., ssh_key_name=...)`.
3. `arvan_wait_for_server` until it's active, read its public IP from the details.
4. `arvan_ssh_run` / `arvan_ssh_run_script` to install and configure software.

Object Storage tools (`arvan_s3_*`) use separate credentials
(ARVAN_S3_ACCESS_KEY/SECRET_KEY); SSH tools default to ARVAN_SSH_USER/ARVAN_SSH_KEY.

Destructive actions (delete server/volume/domain/DNS record/bucket, purge cache,
rebuild, running shell commands) act on real infrastructure — confirm intent first.
"""


def build_server(settings: Settings | None = None) -> tuple[FastMCP, ArvanClient]:
    """Create a configured :class:`FastMCP` server and its API client."""

    settings = settings or Settings.from_env()
    client = ArvanClient(settings)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[dict]:
        try:
            yield {}
        finally:
            task_manager = getattr(_server, "_arvan_task_manager", None)
            if task_manager is not None:
                await task_manager.aclose()
            await client.aclose()

    mcp = FastMCP(
        "ArvanCloud",
        instructions=INSTRUCTIONS,
        lifespan=lifespan,
        host=settings.host,
        port=settings.port,
        stateless_http=settings.stateless_http,
        json_response=settings.json_response,
    )

    try:
        mcp._mcp_server.version = __version__
    except Exception:
        pass

    registered = register_all(mcp, client)
    guardrails = apply_guardrails(mcp, settings)
    logger.info(
        "ArvanCloud MCP %s ready (services: %s, transport: %s, tools: %d%s)",
        __version__,
        ", ".join(registered),
        settings.transport,
        guardrails["active_tools"],
        ", read-only" if settings.read_only else "",
    )
    return mcp, client


def main() -> None:
    """Console-script entry point."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    settings = Settings.from_env()
    if not settings.api_key:
        logger.warning(
            "ARVAN_API_KEY is not set. The server will start and list tools, "
            "but API calls will fail until a machine-user access key is provided."
        )

    mcp, _client = build_server(settings)
    mcp.run(transport=settings.transport)


if __name__ == "__main__":
    main()
