"""Block storage tools — ``/ecc/v1`` (volumes & snapshots).

Object Storage is S3-compatible and is reached through the S3 API with separate
credentials (see ``arvan_capabilities('storage')``), so it is not wrapped here.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._base import compact, resolve_region


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_list_volumes(region: str | None = None) -> Any:
        """List block-storage volumes in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/volumes")

    @mcp.tool()
    async def arvan_get_volume(volume_id: str, region: str | None = None) -> Any:
        """Get a single block-storage volume by id."""

        region = resolve_region(client, region)
        return await client.request(
            "GET", f"/ecc/v1/regions/{region}/volumes/{volume_id}"
        )

    @mcp.tool()
    async def arvan_get_volume_limits(region: str | None = None) -> Any:
        """Get block-storage volume limits/quota for a region."""

        region = resolve_region(client, region)
        return await client.request(
            "GET", f"/ecc/v1/regions/{region}/volumes/limits"
        )

    @mcp.tool()
    async def arvan_create_volume(
        name: str,
        size: int,
        region: str | None = None,
        description: str = "",
    ) -> Any:
        """Create a block-storage volume.

        Args:
            name: Volume name.
            size: Size in GB.
            region: Region code; defaults to ARVAN_DEFAULT_REGION.
            description: Optional description.
        """

        region = resolve_region(client, region)
        body = compact({"name": name, "size": size, "description": description})
        return await client.request(
            "POST", f"/ecc/v1/regions/{region}/volumes", json=body
        )

    @mcp.tool()
    async def arvan_update_volume(
        volume_id: str,
        region: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> Any:
        """Update a volume's name and/or description."""

        region = resolve_region(client, region)
        body = compact({"name": name, "description": description})
        return await client.request(
            "PATCH", f"/ecc/v1/regions/{region}/volumes/{volume_id}", json=body
        )

    @mcp.tool()
    async def arvan_delete_volume(volume_id: str, region: str | None = None) -> Any:
        """Delete a block-storage volume by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/volumes/{volume_id}"
        )

    @mcp.tool()
    async def arvan_attach_volume(
        volume_id: str, server_id: str, region: str | None = None
    ) -> Any:
        """Attach a volume to a server."""

        region = resolve_region(client, region)
        return await client.request(
            "PATCH",
            f"/ecc/v1/regions/{region}/volumes/attach",
            json={"volume_id": volume_id, "server_id": server_id},
        )

    @mcp.tool()
    async def arvan_detach_volume(
        volume_id: str, server_id: str, region: str | None = None
    ) -> Any:
        """Detach a volume from a server."""

        region = resolve_region(client, region)
        return await client.request(
            "PATCH",
            f"/ecc/v1/regions/{region}/volumes/detach",
            json={"volume_id": volume_id, "server_id": server_id},
        )

    @mcp.tool()
    async def arvan_snapshot_volume(
        volume_id: str,
        name: str,
        region: str | None = None,
        description: str = "",
    ) -> Any:
        """Create a snapshot of a volume."""

        region = resolve_region(client, region)
        body = compact({"name": name, "description": description})
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/volumes/{volume_id}/snapshot",
            json=body,
        )
