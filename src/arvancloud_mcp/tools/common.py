"""Cross-cutting tools: the generic request escape hatch and capability catalog.

These are always registered. ``arvan_request`` can reach *any* ArvanCloud
endpoint, guaranteeing the server can use every platform feature even when no
dedicated typed tool exists. ``arvan_capabilities`` lets a client discover what
those endpoints are.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..catalog import CATALOG, summary
from ..client import ArvanAPIError, ArvanClient
from ._exec import which

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]

_OPTIONAL_BINARIES = [
    "terraform", "tflint", "checkov", "kubeconform", "kube-linter", "hadolint",
    "yamllint", "trivy", "gitleaks", "syft", "semgrep", "kubectl", "helm", "git",
    "ping", "traceroute", "whois",
]


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_request(
        method: HttpMethod,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Call any ArvanCloud API endpoint directly (generic escape hatch).

        Use this for any operation that does not have a dedicated tool. Discover
        available endpoints with ``arvan_capabilities``.

        Args:
            method: HTTP method.
            path: Endpoint path relative to the API base, e.g.
                ``/ecc/v1/regions/ir-thr-c2/servers`` or ``/cdn/4.0/domains``.
                A leading slash is optional.
            query: Optional query-string parameters.
            body: Optional JSON request body (for POST/PUT/PATCH).

        Returns:
            The decoded JSON response from ArvanCloud.
        """

        if client.settings.read_only and method.upper() not in ("GET", "HEAD"):
            return {
                "ok": False,
                "error": "server is in read-only mode (ARVAN_READ_ONLY); "
                "only GET/HEAD requests are allowed.",
            }
        return await client.request(method, path, params=query, json=body)

    @mcp.tool()
    async def arvan_capabilities(service: str | None = None) -> dict[str, Any]:
        """Discover ArvanCloud products and their API endpoints.

        Call without arguments for a compact overview of every service. Pass a
        service key (``compute``, ``network``, ``storage``, ``cdn``, ``dns``,
        ``vod``, ``live``) to get its full endpoint list, including request-body
        hints you can feed to ``arvan_request``.
        """

        if not service:
            return summary()

        key = service.strip().lower()
        services = CATALOG["services"]
        if key not in services:
            return {
                "error": f"unknown service '{service}'",
                "available": sorted(services.keys()),
            }
        return {
            "base_url": CATALOG["base_url"],
            "service": key,
            **services[key],
        }

    @mcp.tool()
    async def arvan_doctor() -> dict[str, Any]:
        """Diagnose the server's configuration and connectivity.

        Checks: whether the API key works (a live call), which optional CLI tools
        are installed (IaC/security/k8s/git/net), and whether Object Storage and
        SSH defaults are configured. Run this first to see what's ready to use.
        """

        settings = client.settings
        report: dict[str, Any] = {
            "version_services": list(settings.enabled_services),
            "base_url": settings.base_url,
        }

        if not settings.api_key:
            report["api"] = {"configured": False, "ok": False, "error": "ARVAN_API_KEY not set"}
        else:
            try:
                await client.request("GET", "/ecc/v1/regions")
                report["api"] = {"configured": True, "ok": True}
            except ArvanAPIError as exc:
                report["api"] = {"configured": True, "ok": False, "error": str(exc)}

        report["object_storage"] = {
            "configured": bool(settings.s3_access_key and settings.s3_secret_key),
            "endpoint": settings.s3_endpoint_url(),
        }
        report["ssh"] = {
            "default_user": settings.ssh_user,
            "auth_configured": bool(settings.ssh_key or settings.ssh_key_file or settings.ssh_password),
        }
        report["tools"] = {
            b: which(b) is not None for b in _OPTIONAL_BINARIES
        }
        missing = [b for b, ok in report["tools"].items() if not ok]
        report["hint"] = (
            "Install missing CLI tools (or build the image with "
            "--build-arg INSTALL_IAC_TOOLS=true) to enable: " + ", ".join(missing)
            if missing else "all optional CLI tools are installed"
        )
        return report

    @mcp.tool()
    async def arvan_find_tool(query: str, limit: int = 15) -> dict[str, Any]:
        """Search this server's own tools by keyword (handy with 200+ tools).

        Returns matching tool names and one-line descriptions, ranked by relevance.
        """

        import re

        terms = [t for t in re.split(r"\W+", query.lower()) if t]
        matches = []
        for name, tool in mcp._tool_manager._tools.items():
            desc = (tool.description or "").strip()
            haystack = f"{name} {desc}".lower()
            score = sum(haystack.count(t) for t in terms)
            if score:
                summary_line = desc.splitlines()[0] if desc else ""
                matches.append((score, name, summary_line))
        matches.sort(key=lambda x: (-x[0], x[1]))
        return {
            "query": query,
            "matches": [
                {"tool": n, "description": d} for _s, n, d in matches[: max(1, limit)]
            ],
        }

    @mcp.resource("arvan://capabilities")
    def capabilities_resource() -> dict[str, Any]:
        """The full ArvanCloud API catalogue as an MCP resource."""

        return CATALOG

    @mcp.resource("arvan://regions")
    async def regions_resource() -> Any:
        """Live list of ArvanCloud regions."""

        return await client.request("GET", "/ecc/v1/regions")

    @mcp.resource("arvan://servers/{region}")
    async def servers_resource(region: str) -> Any:
        """Live list of servers in a region."""

        return await client.request("GET", f"/ecc/v1/regions/{region}/servers")

    @mcp.resource("arvan://domains")
    async def domains_resource() -> Any:
        """Live list of CDN/DNS domains on the account."""

        return await client.request("GET", "/cdn/4.0/domains")

    @mcp.prompt()
    def provision_web_server(
        region: str = "ir-thr-c2",
        image: str = "ubuntu/22.04",
        domain: str = "",
    ) -> str:
        """Guide: provision a server, install a web stack, and (optionally) wire DNS."""

        dns_step = (
            f"\n6. Point DNS for {domain} at the server with arvan_create_a_record."
            if domain else ""
        )
        return (
            f"Provision a web server in {region} using image '{image}':\n"
            "1. arvan_list_plans to choose a flavor.\n"
            "2. arvan_security_generate_ssh_keypair (or reuse a key).\n"
            "3. arvan_provision_server with packages=['nginx'] (or install_docker=true).\n"
            "4. arvan_wait_for_server is handled inside provision; note the public IP.\n"
            "5. arvan_net_http_check the IP to confirm it serves traffic." + dns_step +
            "\nReport the server id, IP, and how to reach it."
        )

    @mcp.prompt()
    def audit_security(region: str = "ir-thr-c2") -> str:
        """Guide: run a security audit of a region and a domain."""

        return (
            f"Audit security for region {region}:\n"
            "1. arvan_security_audit_security_groups to find world-open ports.\n"
            "2. For each public service, arvan_net_tls_cert and "
            "arvan_security_http_headers to grade TLS and headers.\n"
            "3. Summarise findings by severity and propose specific tightenings "
            "(which security-group rules to scope to which CIDRs)."
        )

    @mcp.prompt()
    def setup_cdn(domain: str, origin_ip: str = "") -> str:
        """Guide: onboard a domain to the CDN with DNS, caching and SSL."""

        return (
            f"Set up the CDN for {domain}:\n"
            "1. arvan_create_domain to onboard it.\n"
            f"2. arvan_create_a_record for the origin ({origin_ip or '<origin ip>'}), cloud=true.\n"
            "3. arvan_update_caching_settings to enable caching.\n"
            "4. arvan_update_ssl_settings with ssl_type='default' for free HTTPS.\n"
            "5. Confirm with arvan_get_domain and arvan_net_http_check."
        )

    @mcp.prompt()
    def deploy_static_site(bucket: str, local_dir: str = "./site") -> str:
        """Guide: host a static site on Object Storage."""

        return (
            f"Deploy a static site to bucket '{bucket}':\n"
            "1. arvan_s3_create_bucket (acl='public-read').\n"
            f"2. arvan_s3_sync_local_dir from '{local_dir}' (acl='public-read').\n"
            "3. arvan_s3_enable_static_website (index.html/error.html).\n"
            "4. Return the website endpoint."
        )
