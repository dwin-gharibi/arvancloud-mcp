"""Cloud networking tools — ``/ecc/v1`` (networks, security groups, floating IPs)."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._base import compact, resolve_region


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_list_networks(region: str | None = None) -> Any:
        """List networks (public and private) available in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/networks")

    @mcp.tool()
    async def arvan_list_subnets(region: str | None = None) -> Any:
        """List private-network subnets in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/subnets")

    @mcp.tool()
    async def arvan_create_private_network(
        name: str,
        region: str | None = None,
        subnet_ip: str | None = None,
        subnet_gateway: str | None = None,
        enable_gateway: bool = False,
        enable_dhcp: bool = True,
        dns_servers: str | None = None,
        dhcp_start: str | None = None,
        dhcp_end: str | None = None,
    ) -> Any:
        """Create a private network (subnet).

        Args:
            name: Network name.
            region: Region code; defaults to ARVAN_DEFAULT_REGION.
            subnet_ip: CIDR for the subnet, e.g. ``192.168.0.0/24``.
            subnet_gateway: Gateway IP within the subnet.
            enable_gateway: Whether to enable the gateway.
            enable_dhcp: Whether DHCP assigns addresses automatically.
            dns_servers: Comma-separated DNS servers.
            dhcp_start / dhcp_end: Optional DHCP allocation range.
        """

        region = resolve_region(client, region)
        body = compact(
            {
                "name": name,
                "subnet_ip": subnet_ip,
                "subnet_gateway": subnet_gateway,
                "enable_gateway": enable_gateway,
                "enable_dhcp": enable_dhcp,
                "dns_servers": dns_servers,
            }
        )
        if dhcp_start and dhcp_end:
            body["dhcp"] = {"start": dhcp_start, "end": dhcp_end}
        return await client.request(
            "POST", f"/ecc/v1/regions/{region}/subnets", json=body
        )

    @mcp.tool()
    async def arvan_get_subnet(subnet_id: str, region: str | None = None) -> Any:
        """Get a private-network subnet by id."""

        region = resolve_region(client, region)
        return await client.request(
            "GET", f"/ecc/v1/regions/{region}/subnets/{subnet_id}"
        )

    @mcp.tool()
    async def arvan_update_subnet(
        subnet_id: str, fields: dict[str, Any], region: str | None = None
    ) -> Any:
        """Update a subnet (e.g. dns_servers, enable_dhcp, subnet_gateway)."""

        region = resolve_region(client, region)
        return await client.request(
            "PATCH", f"/ecc/v1/regions/{region}/subnets/{subnet_id}", json=fields
        )

    @mcp.tool()
    async def arvan_delete_subnet(subnet_id: str, region: str | None = None) -> Any:
        """Delete a private-network subnet by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/subnets/{subnet_id}"
        )

    @mcp.tool()
    async def arvan_attach_network(
        network_id: str,
        server_id: str,
        region: str | None = None,
        ip: str | None = None,
        enable_port_security: bool = True,
    ) -> Any:
        """Attach a network to a server (optionally with a fixed IP)."""

        region = resolve_region(client, region)
        body = compact(
            {
                "server_id": server_id,
                "ip": ip,
                "enablePortSecurity": enable_port_security,
            }
        )
        return await client.request(
            "PATCH",
            f"/ecc/v1/regions/{region}/networks/{network_id}/attach",
            json=body,
        )

    @mcp.tool()
    async def arvan_detach_network(
        network_id: str, server_id: str, region: str | None = None
    ) -> Any:
        """Detach a network from a server."""

        region = resolve_region(client, region)
        return await client.request(
            "PATCH",
            f"/ecc/v1/regions/{region}/networks/{network_id}/detach",
            json={"server_id": server_id},
        )

    @mcp.tool()
    async def arvan_list_security_groups(region: str | None = None) -> Any:
        """List security groups (firewall groups) in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/securities")

    @mcp.tool()
    async def arvan_create_security_group(
        name: str, description: str = "", region: str | None = None
    ) -> Any:
        """Create a security group."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/securities",
            json={"name": name, "description": description},
        )

    @mcp.tool()
    async def arvan_delete_security_group(
        group_id: str, region: str | None = None
    ) -> Any:
        """Delete a security group by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/securities/{group_id}"
        )

    @mcp.tool()
    async def arvan_create_security_rule(
        group_id: str,
        direction: Literal["ingress", "egress"],
        region: str | None = None,
        protocol: str | None = None,
        port_from: str | None = None,
        port_to: str | None = None,
        ips: list[str] | None = None,
        description: str = "",
    ) -> Any:
        """Add a rule to a security group.

        Args:
            group_id: Target security-group id.
            direction: ``ingress`` (inbound) or ``egress`` (outbound).
            protocol: ``tcp``, ``udp``, ``icmp`` … (omit for any).
            port_from / port_to: Port range (as strings).
            ips: Source/destination CIDRs, e.g. ``["0.0.0.0/0"]``.
            description: Optional description.
        """

        region = resolve_region(client, region)
        body = compact(
            {
                "direction": direction,
                "protocol": protocol,
                "port_from": port_from,
                "port_to": port_to,
                "ips": ips,
                "description": description,
            }
        )
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/securities/security-rules/{group_id}",
            json=body,
        )

    @mcp.tool()
    async def arvan_delete_security_rule(
        rule_id: str, region: str | None = None
    ) -> Any:
        """Delete a security-group rule by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE",
            f"/ecc/v1/regions/{region}/securities/security-rules/{rule_id}",
        )

    @mcp.tool()
    async def arvan_list_floating_ips(region: str | None = None) -> Any:
        """List floating (public) IP addresses in a region."""

        region = resolve_region(client, region)
        return await client.request("GET", f"/ecc/v1/regions/{region}/float-ips")

    @mcp.tool()
    async def arvan_create_floating_ip(
        description: str = "", region: str | None = None
    ) -> Any:
        """Allocate a new floating (public) IP address."""

        region = resolve_region(client, region)
        return await client.request(
            "POST",
            f"/ecc/v1/regions/{region}/float-ips",
            json={"description": description},
        )

    @mcp.tool()
    async def arvan_attach_floating_ip(
        floating_ip_id: str,
        region: str | None = None,
        server_id: str | None = None,
        subnet_id: str | None = None,
        port_id: str | None = None,
    ) -> Any:
        """Attach a floating IP to a server/port."""

        region = resolve_region(client, region)
        body = compact(
            {"server_id": server_id, "subnet_id": subnet_id, "port_id": port_id}
        )
        return await client.request(
            "PATCH",
            f"/ecc/v1/regions/{region}/float-ip/{floating_ip_id}/attach",
            json=body,
        )

    @mcp.tool()
    async def arvan_detach_floating_ip(
        port_id: str, region: str | None = None
    ) -> Any:
        """Detach a floating IP from the given port."""

        region = resolve_region(client, region)
        return await client.request(
            "PATCH",
            f"/ecc/v1/regions/{region}/float-ip/detach",
            json={"port_id": port_id},
        )

    @mcp.tool()
    async def arvan_delete_floating_ip(
        floating_ip_id: str, region: str | None = None
    ) -> Any:
        """Release (delete) a floating IP address by id."""

        region = resolve_region(client, region)
        return await client.request(
            "DELETE", f"/ecc/v1/regions/{region}/float-ips/{floating_ip_id}"
        )

    @mcp.tool()
    async def arvan_set_port_security(
        port_id: str, enabled: bool, region: str | None = None
    ) -> Any:
        """Enable or disable port security on a network port."""

        region = resolve_region(client, region)
        action = "enable" if enabled else "disable"
        return await client.request(
            "POST", f"/ecc/v1/regions/{region}/ports/{port_id}/{action}"
        )
