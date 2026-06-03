"""Cloud Server (IaaS / "Abrak") tools — ``/ecc/v1``."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._base import compact, resolve_region

ServerAction = Literal[
    "power-on",
    "power-off",
    "reboot",
    "hard-reboot",
    "rescue",
    "unrescue",
    "reset-root-password",
    "add-public-ip",
    "change-public-ip",
]


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_list_regions() -> Any:
        """List all ArvanCloud IaaS regions (datacenters) and their codes."""

        return await client.request("GET", "/ecc/v1/regions")

    @mcp.tool()
    async def arvan_account_details() -> Any:
        """Get the current account/project details for Cloud Server."""

        return await client.request("GET", "/ecc/v1/details")

    @mcp.tool()
    async def arvan_get_quotas(region: str | None = None) -> Any:
        """Get resource quotas and current usage for a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/quotas")

    @mcp.tool()
    async def arvan_list_servers(region: str | None = None) -> Any:
        """List cloud servers (VMs) in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/servers")

    @mcp.tool()
    async def arvan_get_server(server_id: str, region: str | None = None) -> Any:
        """Get details of a single cloud server by id."""

        region = resolve_region(client, region)
        return await client.request(
            "GET", f"/ecc/v1/regions/{region}/servers/{server_id}"
        )

    @mcp.tool()
    async def arvan_server_options(region: str | None = None) -> Any:
        """Get available options for creating a server in a region."""

        region = resolve_region(client, region)
        return await client.request(
            "GET", f"/ecc/v1/regions/{region}/servers/options"
        )

    @mcp.tool()
    async def arvan_create_server(
        name: str,
        flavor_id: str,
        image_id: str,
        region: str | None = None,
        disk_size: int = 25,
        count: int = 1,
        network_ids: list[str] | None = None,
        security_group_names: list[str] | None = None,
        ssh_key_name: str | None = None,
        init_script: str | None = None,
        ha_enabled: bool = False,
        create_type: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Create one or more cloud servers.

        Args:
            name: Server name (a numeric suffix is added when count > 1).
            flavor_id: Plan/flavor id — see ``arvan_list_plans``.
            image_id: OS/snapshot image id — see ``arvan_list_images``.
            region: Region code; defaults to ARVAN_DEFAULT_REGION.
            disk_size: Root disk size in GB.
            count: How many identical servers to create.
            network_ids: Private network ids to attach.
            security_group_names: Security groups to apply.
            ssh_key_name: Name of an SSH key to inject (see ``arvan_list_ssh_keys``).
            init_script: Cloud-init / startup script.
            ha_enabled: Enable high availability.
            create_type: Optional create type (e.g. ``image``, ``snapshot``).
            extra: Any additional fields to merge into the request body.
        """

        region = resolve_region(client, region)
        body: dict[str, Any] = compact(
            {
                "name": name,
                "flavor_id": flavor_id,
                "image_id": image_id,
                "disk_size": disk_size,
                "count": count,
                "network_ids": network_ids,
                "init_script": init_script,
                "ha_enabled": ha_enabled,
                "create_type": create_type,
            }
        )
        if security_group_names:
            body["security_groups"] = [{"name": n} for n in security_group_names]
        if ssh_key_name:
            body["ssh_key"] = True
            body["key_name"] = ssh_key_name
        if extra:
            body.update(extra)
        return await client.request(
            "POST", f"/ecc/v1/regions/{region}/servers", json=body
        )

    @mcp.tool()
    async def arvan_delete_server(
        server_id: str,
        region: str | None = None,
        force_delete_floating_ips: bool = False,
    ) -> Any:
        """Delete a cloud server. Set force_delete_floating_ips to also release IPs."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE",
            f"/ecc/v1/regions/{region}/servers/{server_id}",
            params={"forceDeleteFloatingIp": force_delete_floating_ips},
        )

    @mcp.tool()
    async def arvan_server_action(
        server_id: str,
        action: ServerAction,
        region: str | None = None,
    ) -> Any:
        """Run a power/maintenance action on a server.

        Actions: power-on, power-off, reboot, hard-reboot, rescue, unrescue,
        reset-root-password, add-public-ip, change-public-ip.
        """

        region = resolve_region(client, region)
        return await client.request(
            "POST", f"/ecc/v1/regions/{region}/servers/{server_id}/{action}"
        )

    @mcp.tool()
    async def arvan_rename_server(
        server_id: str, name: str, region: str | None = None
    ) -> Any:
        """Rename a cloud server."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/servers/{server_id}/rename",
            json={"name": name},
        )

    @mcp.tool()
    async def arvan_rebuild_server(
        server_id: str, image_id: str, region: str | None = None
    ) -> Any:
        """Rebuild a server from an image (destroys current root disk contents)."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/servers/{server_id}/rebuild",
            json={"image_id": image_id},
        )

    @mcp.tool()
    async def arvan_resize_server(
        server_id: str, flavor_id: str, region: str | None = None
    ) -> Any:
        """Change a server's plan/flavor (resize CPU & RAM)."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/servers/{server_id}/resize",
            json={"flavor_id": flavor_id},
        )

    @mcp.tool()
    async def arvan_resize_server_disk(
        server_id: str, size: int, region: str | None = None
    ) -> Any:
        """Resize a server's root disk to the given size in GB."""

        region = resolve_region(client, region)
        return await client.request(
            "PUT",
            f"/ecc/v1/regions/{region}/servers/{server_id}/resizeRoot",
            json={"size": size},
        )

    @mcp.tool()
    async def arvan_list_images(
        region: str | None = None,
        image_type: str | None = None,
        marketplace: bool = False,
    ) -> Any:
        """List server images.

        Args:
            region: Region code; defaults to ARVAN_DEFAULT_REGION.
            image_type: Filter by type, e.g. ``distributions`` (OS images),
                ``snapshots`` (your snapshots), or ``private``.
            marketplace: Set True to list marketplace app images instead.
        """

        region = resolve_region(client, region)
        if marketplace:
            return await client.request(
                "GET", f"/ecc/v1/regions/{region}/images/marketplace"
            )
        params = {"type": image_type} if image_type else None
        return await client.request(
            "GET", f"/ecc/v1/regions/{region}/images", params=params
        )

    @mcp.tool()
    async def arvan_list_plans(region: str | None = None) -> Any:
        """List available server plans/flavors (sizes) and their pricing."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/sizes")

    @mcp.tool()
    async def arvan_list_ptr_records(region: str | None = None) -> Any:
        """List reverse-DNS (PTR) records in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/ptr")

    @mcp.tool()
    async def arvan_create_ptr_record(
        ip: str, domain: str, region: str | None = None
    ) -> Any:
        """Create a reverse-DNS (PTR) record mapping an IP to a domain."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/ptr",
            json={"ip": ip, "domain": domain},
        )

    @mcp.tool()
    async def arvan_delete_ptr_record(
        ptr_id: str, region: str | None = None
    ) -> Any:
        """Delete a reverse-DNS (PTR) record by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/ptr/{ptr_id}"
        )

    @mcp.tool()
    async def arvan_list_ssh_keys(region: str | None = None) -> Any:
        """List SSH keys registered in a region (for injecting into new servers)."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/ssh-keys")

    @mcp.tool()
    async def arvan_create_ssh_key(
        name: str, public_key: str, region: str | None = None
    ) -> Any:
        """Register an SSH public key so it can be injected into servers at create."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/ssh-keys",
            json={"name": name, "public_key": public_key},
        )

    @mcp.tool()
    async def arvan_delete_ssh_key(name: str, region: str | None = None) -> Any:
        """Delete a registered SSH key by name."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/ssh-keys/{name}"
        )

    @mcp.tool()
    async def arvan_list_tags(region: str | None = None) -> Any:
        """List resource tags in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/tags")

    @mcp.tool()
    async def arvan_create_tag(
        name: str,
        region: str | None = None,
        color: str | None = None,
    ) -> Any:
        """Create a resource tag."""

        region = resolve_region(client, region)
        body = compact({"name": name, "color": color})
        return await client.request(
            "POST", f"/ecc/v1/regions/{region}/tags", json=body
        )

    @mcp.tool()
    async def arvan_delete_tag(tag_id: str, region: str | None = None) -> Any:
        """Delete a resource tag by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/tags/{tag_id}"
        )

    @mcp.tool()
    async def arvan_attach_tag(
        tag_id: str,
        instance_id: str,
        instance_type: str = "server",
        region: str | None = None,
    ) -> Any:
        """Attach a tag to a resource (e.g. a server)."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/tags/{tag_id}/attach",
            json={"instance_id": instance_id, "instance_type": instance_type},
        )

    @mcp.tool()
    async def arvan_detach_tag(
        tag_id: str,
        instance_id: str,
        instance_type: str = "server",
        region: str | None = None,
    ) -> Any:
        """Detach a tag from a resource."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/tags/{tag_id}/detach",
            json={"instance_id": instance_id, "instance_type": instance_type},
        )

    @mcp.tool()
    async def arvan_attach_security_group_to_server(
        server_id: str, security_group_id: str, region: str | None = None
    ) -> Any:
        """Attach a security group to a server."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/servers/{server_id}/add-security-group",
            json={"security_group_id": security_group_id},
        )

    @mcp.tool()
    async def arvan_detach_security_group_from_server(
        server_id: str, security_group_id: str, region: str | None = None
    ) -> Any:
        """Detach a security group from a server."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/servers/{server_id}/remove-security-group",
            json={"security_group_id": security_group_id},
        )

    @mcp.tool()
    async def arvan_wait_for_server(
        server_id: str,
        region: str | None = None,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> Any:
        """Poll a server until it becomes active (or the timeout elapses).

        Handy right after ``arvan_create_server`` and before SSHing in. Returns
        the latest server details plus ``ready``/``timed_out`` flags. The wait is
        bounded to 30 minutes regardless of ``timeout``.
        """

        region = resolve_region(client, region)
        deadline = time.monotonic() + min(timeout, 1800.0)
        ready_states = {"active", "running", "up", "started"}
        while True:
            data = await client.request(
                "GET", f"/ecc/v1/regions/{region}/servers/{server_id}"
            )
            details = data.get("data", data) if isinstance(data, dict) else data
            status = ""
            if isinstance(details, dict):
                status = str(details.get("status") or "")
            if status.lower() in ready_states:
                return {"ready": True, "status": status, "server": details}
            if time.monotonic() >= deadline:
                return {
                    "ready": False,
                    "timed_out": True,
                    "status": status,
                    "server": details,
                }
            await asyncio.sleep(min(interval, 15.0))
