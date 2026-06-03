"""Cloud DNS tools — ``/cdn/4.0/domains/{domain}/dns-records``.

Record ``value`` shapes vary by type:
    * a / aaaa : list of ``{"ip": "1.2.3.4", "port"?, "weight"?, "country"?}``
    * cname / aname : ``{"host": "example.com", "host_header"?}``
    * mx : list of ``{"host": "mail.example.com", "priority": 10}``
    * txt / spf : ``{"text": "..."}``
    * ns : ``{"host": "ns1.example.com"}``
    * srv : list of ``{"host", "port", "priority", "weight"}``
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._base import compact

DnsType = Literal[
    "a", "aaaa", "cname", "mx", "txt", "ns", "srv", "spf", "ptr", "aname", "caa", "tlsa", "dkim"
]


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_list_dns_records(
        domain: str,
        search: str | None = None,
        type: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> Any:
        """List DNS records for a domain (optionally filter by search/type)."""

        params = compact(
            {"search": search, "type": type, "page": page, "per_page": per_page}
        )
        return await client.request(
            "GET", f"/cdn/4.0/domains/{domain}/dns-records", params=params
        )

    @mcp.tool()
    async def arvan_get_dns_record(domain: str, record_id: str) -> Any:
        """Get a single DNS record by id."""

        return await client.request(
            "GET", f"/cdn/4.0/domains/{domain}/dns-records/{record_id}"
        )

    @mcp.tool()
    async def arvan_create_dns_record(
        domain: str,
        type: DnsType,
        name: str,
        value: Any,
        ttl: int = 120,
        cloud: bool = False,
        upstream_https: str | None = None,
        ip_filter_mode: dict[str, Any] | None = None,
    ) -> Any:
        """Create a DNS record. See module docs for ``value`` shapes per type.

        Args:
            domain: Zone the record belongs to.
            type: Record type (a, aaaa, cname, mx, txt, ns, srv, …).
            name: Record name/subdomain (``@`` for the root).
            value: Type-specific value (see the shapes in this tool's docs).
            ttl: Time-to-live in seconds.
            cloud: Whether to proxy the record through ArvanCloud (orange-cloud).
            upstream_https: Upstream HTTPS mode when cloud is enabled.
            ip_filter_mode: Optional IP-filter/health-check configuration.
        """

        body = compact(
            {
                "type": type,
                "name": name,
                "value": value,
                "ttl": ttl,
                "cloud": cloud,
                "upstream_https": upstream_https,
                "ip_filter_mode": ip_filter_mode,
            }
        )
        return await client.request(
            "POST", f"/cdn/4.0/domains/{domain}/dns-records", json=body
        )

    @mcp.tool()
    async def arvan_create_a_record(
        domain: str,
        name: str,
        ips: list[str],
        ttl: int = 120,
        cloud: bool = False,
    ) -> Any:
        """Convenience: create an A record pointing ``name`` at one or more IPs."""

        value = [{"ip": ip} for ip in ips]
        return await arvan_create_dns_record(
            domain=domain, type="a", name=name, value=value, ttl=ttl, cloud=cloud
        )

    @mcp.tool()
    async def arvan_create_cname_record(
        domain: str,
        name: str,
        target: str,
        ttl: int = 120,
        cloud: bool = False,
    ) -> Any:
        """Convenience: create a CNAME record from ``name`` to ``target``."""

        return await arvan_create_dns_record(
            domain=domain,
            type="cname",
            name=name,
            value={"host": target},
            ttl=ttl,
            cloud=cloud,
        )

    @mcp.tool()
    async def arvan_update_dns_record(
        domain: str, record_id: str, record: dict[str, Any]
    ) -> Any:
        """Update a DNS record (full replace).

        ``record`` should contain the same fields as creation
        (``type``, ``name``, ``value``, ``ttl``, ``cloud`` …).
        """

        return await client.request(
            "PUT",
            f"/cdn/4.0/domains/{domain}/dns-records/{record_id}",
            json=record,
        )

    @mcp.tool()
    async def arvan_delete_dns_record(domain: str, record_id: str) -> Any:
        """Delete a DNS record by id."""

        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/dns-records/{record_id}"
        )

    @mcp.tool()
    async def arvan_toggle_dns_cloud(
        domain: str, record_id: str, cloud: bool
    ) -> Any:
        """Enable or disable cloud (proxy) for a DNS record."""

        return await client.request(
            "PUT",
            f"/cdn/4.0/domains/{domain}/dns-records/{record_id}/cloud",
            json={"cloud": cloud},
        )

    @mcp.tool()
    async def arvan_import_dns_zone(domain: str, zone: str) -> Any:
        """Import DNS records from a BIND-style zone file.

        ``zone`` is the text content of the zone file; it is uploaded as the
        ``f_zone_file`` multipart field the API expects.
        """

        files = {"f_zone_file": ("zone.txt", zone.encode("utf-8"), "text/plain")}
        return await client.request(
            "POST",
            f"/cdn/4.0/domains/{domain}/dns-records/import",
            files=files,
        )

    @mcp.tool()
    async def arvan_get_dnssec(domain: str) -> Any:
        """Get DNSSEC status (and DS records) for a domain."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}/dnssec")

    @mcp.tool()
    async def arvan_set_dnssec(domain: str, enabled: bool) -> Any:
        """Enable or disable DNSSEC for a domain."""

        return await client.request(
            "PUT",
            f"/cdn/4.0/domains/{domain}/dnssec/actions",
            json={"enable": enabled},
        )
