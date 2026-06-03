"""Networking diagnostics — DNS, connectivity, HTTP, TLS, and a load tester.

These complement the cloud tools: after you provision a server or change DNS,
use these to verify reachability, DNS propagation, HTTP health and TLS validity.
Pure-Python where possible (dnspython, httpx, ssl/cryptography); ping/traceroute/
whois shell out and degrade gracefully when the binary is absent.
"""

from __future__ import annotations

import asyncio
import socket
import statistics
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._exec import run_command

_DEFAULT_TIMEOUT = 5.0


def register(mcp: FastMCP, client: ArvanClient) -> None:
    settings = client.settings

    @mcp.tool()
    async def arvan_net_dns_lookup(
        name: str,
        record_type: str = "A",
        nameserver: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Any:
        """Resolve a DNS record.

        Args:
            name: Hostname to look up.
            record_type: A, AAAA, CNAME, MX, TXT, NS, SOA, SRV, CAA, PTR …
            nameserver: Optional resolver IP to query directly (test propagation).
            timeout: Query timeout in seconds.
        """

        def _resolve() -> Any:
            import dns.resolver

            resolver = dns.resolver.Resolver(configure=True)
            resolver.lifetime = timeout
            resolver.timeout = timeout
            if nameserver:
                resolver.nameservers = [nameserver]
            try:
                answers = resolver.resolve(name, record_type.upper())
            except Exception as exc:
                return {"name": name, "type": record_type.upper(), "error": str(exc), "records": []}
            return {
                "name": name,
                "type": record_type.upper(),
                "ttl": answers.rrset.ttl if answers.rrset else None,
                "records": [r.to_text() for r in answers],
            }

        return await asyncio.to_thread(_resolve)

    @mcp.tool()
    async def arvan_net_reverse_dns(ip: str) -> Any:
        """Reverse-resolve an IP address to a hostname (PTR)."""

        def _ptr() -> Any:
            try:
                host, _alias, _addrs = socket.gethostbyaddr(ip)
                return {"ip": ip, "hostname": host}
            except OSError as exc:
                return {"ip": ip, "error": str(exc)}

        return await asyncio.to_thread(_ptr)

    @mcp.tool()
    async def arvan_net_tcp_check(
        host: str, port: int, timeout: float = _DEFAULT_TIMEOUT
    ) -> Any:
        """Check whether a TCP port is open and measure connect latency."""

        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return {
                "host": host,
                "port": port,
                "open": True,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        except (OSError, asyncio.TimeoutError) as exc:
            return {"host": host, "port": port, "open": False, "error": str(exc)}

    @mcp.tool()
    async def arvan_net_port_scan(
        host: str,
        ports: list[int] | None = None,
        timeout: float = 2.0,
    ) -> Any:
        """Scan a list of TCP ports on a host (defaults to common service ports)."""

        targets = ports or [22, 80, 443, 3306, 5432, 6379, 8080, 8443, 27017]
        targets = targets[:100]

        async def _check(port: int) -> tuple[int, bool]:
            try:
                _r, w = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=timeout
                )
                w.close()
                return port, True
            except (OSError, asyncio.TimeoutError):
                return port, False

        results = await asyncio.gather(*(_check(p) for p in targets))
        return {
            "host": host,
            "open_ports": [p for p, ok in results if ok],
            "closed_ports": [p for p, ok in results if not ok],
        }

    @mcp.tool()
    async def arvan_net_http_check(
        url: str,
        method: str = "GET",
        timeout: float = 10.0,
        follow_redirects: bool = True,
    ) -> Any:
        """Make an HTTP(S) request and report status, timing, and key headers."""

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=follow_redirects, verify=settings.verify_ssl
            ) as hc:
                resp = await hc.request(method.upper(), url)
        except httpx.HTTPError as exc:
            return {"url": url, "ok": False, "error": str(exc)}
        return {
            "url": url,
            "ok": resp.status_code < 400,
            "status_code": resp.status_code,
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
            "final_url": str(resp.url),
            "redirects": len(resp.history),
            "server": resp.headers.get("server"),
            "content_type": resp.headers.get("content-type"),
            "content_length": resp.headers.get("content-length"),
        }

    @mcp.tool()
    async def arvan_net_http_load_test(
        url: str,
        requests: int = 50,
        concurrency: int = 10,
        method: str = "GET",
        timeout: float = 10.0,
    ) -> Any:
        """Fire a quick concurrent load test and report latency percentiles.

        Bounded to 2000 requests and 200 concurrency. Useful for sanity-checking
        a freshly deployed endpoint, not a substitute for a real load tool.
        """

        requests = max(1, min(requests, 2000))
        concurrency = max(1, min(concurrency, 200))
        sem = asyncio.Semaphore(concurrency)
        latencies: list[float] = []
        statuses: dict[int, int] = {}
        errors = 0

        async with httpx.AsyncClient(
            timeout=timeout, verify=settings.verify_ssl
        ) as hc:

            async def _one() -> None:
                nonlocal errors
                async with sem:
                    t0 = time.perf_counter()
                    try:
                        resp = await hc.request(method.upper(), url)
                        latencies.append((time.perf_counter() - t0) * 1000)
                        statuses[resp.status_code] = statuses.get(resp.status_code, 0) + 1
                    except httpx.HTTPError:
                        errors += 1

            wall_start = time.perf_counter()
            await asyncio.gather(*(_one() for _ in range(requests)))
            wall = time.perf_counter() - wall_start

        def _pct(values: list[float], p: float) -> float | None:
            if not values:
                return None
            ordered = sorted(values)
            idx = min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1))))
            return round(ordered[idx], 2)

        ok = len(latencies)
        return {
            "url": url,
            "requests": requests,
            "concurrency": concurrency,
            "successful": ok,
            "errors": errors,
            "status_counts": statuses,
            "rps": round(requests / wall, 2) if wall > 0 else None,
            "latency_ms": {
                "min": round(min(latencies), 2) if latencies else None,
                "mean": round(statistics.mean(latencies), 2) if latencies else None,
                "p50": _pct(latencies, 50),
                "p95": _pct(latencies, 95),
                "p99": _pct(latencies, 99),
                "max": round(max(latencies), 2) if latencies else None,
            },
        }

    @mcp.tool()
    async def arvan_net_tls_cert(
        host: str, port: int = 443, timeout: float = _DEFAULT_TIMEOUT
    ) -> Any:
        """Inspect the TLS certificate served by a host (issuer, SANs, expiry)."""

        def _inspect() -> Any:
            import ssl
            from datetime import datetime, timezone

            from cryptography import x509
            from cryptography.x509.oid import NameOID

            ctx = ssl._create_unverified_context()
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    der = ssock.getpeercert(binary_form=True)
                    proto = ssock.version()
            cert = x509.load_der_x509_certificate(der)

            def _cn(name: x509.Name) -> str:
                attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
                return str(attrs[0].value) if attrs else name.rfc4514_string()

            not_after = getattr(cert, "not_valid_after_utc", None)
            if not_after is not None:
                now = datetime.now(timezone.utc)
            else:
                not_after = cert.not_valid_after
                now = datetime.utcnow()
            try:
                sans = cert.extensions.get_extension_for_class(
                    x509.SubjectAlternativeName
                ).value.get_values_for_type(x509.DNSName)
            except x509.ExtensionNotFound:
                sans = []

            return {
                "host": host,
                "port": port,
                "tls_version": proto,
                "subject": _cn(cert.subject),
                "issuer": _cn(cert.issuer),
                "not_after": not_after.isoformat(),
                "days_until_expiry": (not_after - now).days,
                "expired": not_after < now,
                "subject_alt_names": sans,
                "serial_number": format(cert.serial_number, "x"),
            }

        try:
            return await asyncio.to_thread(_inspect)
        except OSError as exc:
            return {"host": host, "port": port, "error": str(exc)}

    @mcp.tool()
    async def arvan_net_ping(host: str, count: int = 4) -> Any:
        """ICMP ping a host (requires the system ``ping`` binary)."""

        count = max(1, min(count, 20))
        return await run_command(
            ["ping", "-c", str(count), host], timeout=float(count) * 2 + 10
        )

    @mcp.tool()
    async def arvan_net_traceroute(host: str, max_hops: int = 30) -> Any:
        """Trace the network path to a host (requires ``traceroute``)."""

        max_hops = max(1, min(max_hops, 64))
        return await run_command(
            ["traceroute", "-m", str(max_hops), host], timeout=60.0
        )

    @mcp.tool()
    async def arvan_net_whois(query: str) -> Any:
        """WHOIS lookup for a domain or IP (requires the ``whois`` binary)."""

        return await run_command(["whois", query], timeout=30.0)

    @mcp.tool()
    async def arvan_net_my_public_ip() -> Any:
        """Return this server's public IP address (via an external echo service)."""

        try:
            async with httpx.AsyncClient(timeout=10.0) as hc:
                resp = await hc.get("https://api.ipify.org", params={"format": "json"})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            return {"error": str(exc)}
