"""CDN & Cloud Security tools — ``/cdn/4.0``."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._base import compact


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_list_domains(
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
    ) -> Any:
        """List CDN domains on the account (supports pagination & search)."""

        params = compact({"page": page, "per_page": per_page, "search": search})
        return await client.request("GET", "/cdn/4.0/domains", params=params)

    @mcp.tool()
    async def arvan_get_domain(domain: str) -> Any:
        """Get details and settings for a CDN domain."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}")

    @mcp.tool()
    async def arvan_create_domain(
        domain: str,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Add a domain to the CDN / Cloud DNS (the "dns-service" onboarding call).

        Args:
            domain: The domain name, e.g. ``example.com``.
            extra: Additional fields to merge into the request body (e.g. plan).
        """

        body: dict[str, Any] = {"domain": domain}
        if extra:
            body.update(extra)
        return await client.request(
            "POST", "/cdn/4.0/domains/dns-service", json=body
        )

    @mcp.tool()
    async def arvan_delete_domain(
        domain: str, domain_id: str | None = None
    ) -> Any:
        """Remove a domain from the CDN.

        The delete endpoint requires the domain's id. If ``domain_id`` is not
        supplied it is looked up automatically via the domain details.
        """

        if not domain_id:
            info = await client.request("GET", f"/cdn/4.0/domains/{domain}")
            data = info.get("data", info) if isinstance(info, dict) else {}
            if isinstance(data, dict):
                domain_id = data.get("id")
        params = {"id": domain_id} if domain_id else None
        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}", params=params
        )

    @mcp.tool()
    async def arvan_get_caching_settings(domain: str) -> Any:
        """Get caching settings for a domain."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}/caching")

    @mcp.tool()
    async def arvan_update_caching_settings(
        domain: str, settings: dict[str, Any]
    ) -> Any:
        """Update caching settings for a domain.

        ``settings`` accepts the caching fields documented by ArvanCloud, e.g.
        ``{"cache_status": "enable", "cache_page_200": "..."}``.
        """

        return await client.request(
            "PATCH", f"/cdn/4.0/domains/{domain}/caching", json=settings
        )

    @mcp.tool()
    async def arvan_purge_cache(
        domain: str, urls: list[str] | None = None
    ) -> Any:
        """Purge cached content for a domain.

        Pass ``urls`` to purge specific paths, or omit to purge everything.
        """

        body: dict[str, Any] = {
            "purge": "individual" if urls else "all",
            "purge_urls": urls,
        }
        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/caching", json=body
        )

    @mcp.tool()
    async def arvan_list_page_rules(domain: str) -> Any:
        """List page rules for a domain."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}/page-rules")

    @mcp.tool()
    async def arvan_create_page_rule(
        domain: str, url: str, actions: dict[str, Any]
    ) -> Any:
        """Create a page rule.

        Args:
            domain: The CDN domain.
            url: URL pattern the rule applies to (e.g. ``example.com/blog/*``).
            actions: Map of rule actions, e.g. ``{"cache_level": "bypass"}``.
        """

        return await client.request(
            "POST",
            f"/cdn/4.0/domains/{domain}/page-rules",
            json={"url": url, "actions": actions},
        )

    @mcp.tool()
    async def arvan_delete_page_rule(domain: str, rule_id: str) -> Any:
        """Delete a page rule by id."""

        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/page-rules/{rule_id}"
        )

    @mcp.tool()
    async def arvan_list_firewall_rules(domain: str) -> Any:
        """List firewall (WAF) rules for a domain."""

        return await client.request(
            "GET", f"/cdn/4.0/domains/{domain}/firewall/rules"
        )

    @mcp.tool()
    async def arvan_create_firewall_rule(
        domain: str,
        name: str,
        action: str,
        filters: dict[str, Any] | list[Any],
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Create a firewall (WAF) rule.

        Args:
            domain: The CDN domain.
            name: Rule name.
            action: Action to take, e.g. ``block``, ``allow``, ``challenge``.
            filters: Match conditions for the rule.
            extra: Additional fields to merge into the request body.
        """

        body = compact({"name": name, "action": action, "filters": filters})
        if extra:
            body.update(extra)
        return await client.request(
            "POST", f"/cdn/4.0/domains/{domain}/firewall/rules", json=body
        )

    @mcp.tool()
    async def arvan_get_ssl_settings(domain: str) -> Any:
        """Get HTTPS/SSL settings for a domain."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}/ssl")

    @mcp.tool()
    async def arvan_update_ssl_settings(
        domain: str,
        ssl_type: Literal["default", "manual", "off"] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Any:
        """Update HTTPS/SSL settings for a domain.

        Pass ``ssl_type`` (``default`` for free Let's Encrypt, ``manual`` for an
        uploaded certificate, ``off`` to disable) and/or a full ``settings`` body.
        """

        body: dict[str, Any] = dict(settings or {})
        if ssl_type is not None:
            body["ssl_type"] = ssl_type
        return await client.request(
            "PATCH", f"/cdn/4.0/domains/{domain}/ssl", json=body
        )

    @mcp.tool()
    async def arvan_delete_firewall_rule(domain: str, rule_id: str) -> Any:
        """Delete a firewall (WAF) rule by id."""

        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/firewall/rules/{rule_id}"
        )

    @mcp.tool()
    async def arvan_list_rate_limit_rules(domain: str) -> Any:
        """List rate-limit rules for a domain."""

        return await client.request(
            "GET", f"/cdn/4.0/domains/{domain}/rate-limit/rules"
        )

    @mcp.tool()
    async def arvan_create_rate_limit_rule(
        domain: str, rule: dict[str, Any]
    ) -> Any:
        """Create a rate-limit rule.

        ``rule`` carries the documented fields (e.g. ``url``, ``method``,
        ``count``, ``duration``, ``action``).
        """

        return await client.request(
            "POST", f"/cdn/4.0/domains/{domain}/rate-limit/rules", json=rule
        )

    @mcp.tool()
    async def arvan_delete_rate_limit_rule(domain: str, rule_id: str) -> Any:
        """Delete a rate-limit rule by id."""

        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/rate-limit/rules/{rule_id}"
        )

    @mcp.tool()
    async def arvan_list_log_forwarders(domain: str) -> Any:
        """List log-forwarding destinations for a domain."""

        return await client.request(
            "GET", f"/cdn/4.0/domains/{domain}/log-forwarders"
        )

    @mcp.tool()
    async def arvan_create_log_forwarder(
        domain: str, config: dict[str, Any]
    ) -> Any:
        """Create a log forwarder (ship access logs to an external sink)."""

        return await client.request(
            "POST", f"/cdn/4.0/domains/{domain}/log-forwarders", json=config
        )

    @mcp.tool()
    async def arvan_delete_log_forwarder(domain: str, forwarder_id: str) -> Any:
        """Delete a log forwarder by id."""

        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/log-forwarders/{forwarder_id}"
        )

    @mcp.tool()
    async def arvan_list_metric_exporters(domain: str) -> Any:
        """List Prometheus-style metric exporters for a domain."""

        return await client.request(
            "GET", f"/cdn/4.0/domains/{domain}/metric-exporters"
        )

    @mcp.tool()
    async def arvan_create_metric_exporter(
        domain: str, config: dict[str, Any]
    ) -> Any:
        """Create a metric exporter for a domain."""

        return await client.request(
            "POST", f"/cdn/4.0/domains/{domain}/metric-exporters", json=config
        )

    @mcp.tool()
    async def arvan_list_cdn_apps(domain: str) -> Any:
        """List CDN apps configured for a domain."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}/apps")

    @mcp.tool()
    async def arvan_get_cdn_app(domain: str, app_id: str) -> Any:
        """Get a CDN app by id."""

        return await client.request("GET", f"/cdn/4.0/domains/{domain}/apps/{app_id}")

    @mcp.tool()
    async def arvan_create_cdn_app(domain: str, app: dict[str, Any]) -> Any:
        """Create a CDN app (edge application) for a domain."""

        return await client.request(
            "POST", f"/cdn/4.0/domains/{domain}/apps", json=app
        )

    @mcp.tool()
    async def arvan_update_cdn_app(
        domain: str, app_id: str, fields: dict[str, Any]
    ) -> Any:
        """Update a CDN app with the given fields."""

        return await client.request(
            "PATCH", f"/cdn/4.0/domains/{domain}/apps/{app_id}", json=fields
        )

    @mcp.tool()
    async def arvan_delete_cdn_app(domain: str, app_id: str) -> Any:
        """Delete a CDN app by id."""

        return await client.request(
            "DELETE", f"/cdn/4.0/domains/{domain}/apps/{app_id}"
        )

    @mcp.tool()
    async def arvan_trigger_cdn_app_webhook(domain: str, app_id: str) -> Any:
        """Trigger a CDN app's webhook action."""

        return await client.request(
            "POST",
            f"/cdn/4.0/domains/{domain}/apps/{app_id}/actions/trigger_webhook",
        )
