"""Live Streaming tools — ``/live/2.0``.

Mirrors the VOD platform's shape. For sub-resources or fields not wrapped here,
use ``arvan_request`` (paths are listed by ``arvan_capabilities('live')``).
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_live_list_channels(
        page: int | None = None, per_page: int | None = None
    ) -> Any:
        """List live-streaming channels."""

        params = {k: v for k, v in {"page": page, "per_page": per_page}.items() if v}
        return await client.request("GET", "/live/2.0/channels", params=params)

    @mcp.tool()
    async def arvan_live_get_channel(channel_id: str) -> Any:
        """Get a live channel by id (includes push/pull URLs and stream keys)."""

        return await client.request("GET", f"/live/2.0/channels/{channel_id}")

    @mcp.tool()
    async def arvan_live_create_channel(
        title: str,
        description: str = "",
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Create a live-streaming channel.

        ``extra`` carries optional fields such as ``type`` (e.g. ``normal``),
        ``archive_enabled``, ``mode`` and ``slug``.
        """

        body: dict[str, Any] = {"title": title, "description": description}
        if extra:
            body.update(extra)
        return await client.request("POST", "/live/2.0/channels", json=body)

    @mcp.tool()
    async def arvan_live_update_channel(
        channel_id: str, fields: dict[str, Any]
    ) -> Any:
        """Update a live channel with the given fields."""

        return await client.request(
            "PATCH", f"/live/2.0/channels/{channel_id}", json=fields
        )

    @mcp.tool()
    async def arvan_live_delete_channel(channel_id: str) -> Any:
        """Delete a live channel by id."""

        return await client.request("DELETE", f"/live/2.0/channels/{channel_id}")

    @mcp.tool()
    async def arvan_live_list_inputs(channel_id: str) -> Any:
        """List the inputs/streams configured for a live channel."""

        return await client.request(
            "GET", f"/live/2.0/channels/{channel_id}/inputs"
        )
