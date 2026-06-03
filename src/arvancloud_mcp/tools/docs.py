"""Read and search ArvanCloud's product documentation.

``arvan_docs_search`` ranks a curated index of doc topics against a query;
``arvan_docs_fetch`` downloads a docs page and returns it as plain text. Fetching
is restricted to ArvanCloud domains.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient

_ALLOWED_HOST_SUFFIXES = ("arvancloud.ir", "arvancloud.com")
_MAX_DOC_CHARS = 12000

_DOC_INDEX: list[dict[str, str]] = [
    {"title": "API usage & authentication", "url": "https://docs.arvancloud.ir/en/developer-tools/api/api-usage", "tags": "api auth apikey machine user token getting started"},
    {"title": "Create API/access key", "url": "https://docs.arvancloud.ir/en/developer-tools/api/api-key", "tags": "api key access machine user credentials"},
    {"title": "Cloud Server (IaaS) getting started", "url": "https://docs.arvancloud.ir/en/cloud-server/", "tags": "cloud server iaas abrak vm instance compute getting started"},
    {"title": "Cloud Server instances", "url": "https://docs.arvancloud.ir/en/cloud-server/instance/", "tags": "instance server vm create power resize"},
    {"title": "Cloud Server snapshots", "url": "https://docs.arvancloud.ir/en/cloud-server/images/snapshot", "tags": "snapshot backup image server"},
    {"title": "Cloud Server IAM / access management", "url": "https://docs.arvancloud.ir/en/cloud-server/iam/", "tags": "iam access management members roles policies resource groups machine user"},
    {"title": "Terraform with Cloud Server", "url": "https://docs.arvancloud.ir/en/developer-tools/terraform/", "tags": "terraform iac provider provisioning"},
    {"title": "CDN getting started", "url": "https://docs.arvancloud.ir/en/cdn/", "tags": "cdn domain getting started"},
    {"title": "DNS records", "url": "https://docs.arvancloud.ir/en/cdn/dns-records/", "tags": "dns records a aaaa cname mx txt ns srv dnssec"},
    {"title": "DNS records: cloud (proxy) option", "url": "https://docs.arvancloud.ir/en/cdn/dns-records/cloud", "tags": "dns cloud proxy orange record"},
    {"title": "Caching settings", "url": "https://docs.arvancloud.ir/en/cdn/caching/", "tags": "cache caching purge ttl"},
    {"title": "Page rules", "url": "https://docs.arvancloud.ir/en/cdn/page-rules/", "tags": "page rules redirect cache level"},
    {"title": "Firewall (WAF)", "url": "https://docs.arvancloud.ir/en/cdn/security/firewall", "tags": "firewall waf security rules"},
    {"title": "Rate limit", "url": "https://docs.arvancloud.ir/en/cdn/security/rate-limit", "tags": "rate limit security throttle"},
    {"title": "IP lists", "url": "https://docs.arvancloud.ir/en/cdn/list/", "tags": "ip lists allow block whitelist"},
    {"title": "Reports & analytics", "url": "https://docs.arvancloud.ir/en/cdn/analytics/", "tags": "reports analytics metrics traffic"},
    {"title": "Log forwarding", "url": "https://docs.arvancloud.ir/en/cdn/analytics/log-forwarding", "tags": "log forwarding logs siem"},
    {"title": "Object Storage buckets", "url": "https://docs.arvancloud.ir/en/object-storage/buckets", "tags": "object storage s3 bucket"},
    {"title": "Object Storage SDK & credentials", "url": "https://docs.arvancloud.ir/en/developer-tools/sdk/object-storage/", "tags": "object storage s3 boto3 sdk access secret key endpoint"},
    {"title": "Video platform (VOD)", "url": "https://docs.arvancloud.ir/en/video-platform/", "tags": "vod video on demand channels videos subtitles"},
    {"title": "Live streaming", "url": "https://docs.arvancloud.ir/en/vod/live/", "tags": "live streaming channels rtmp"},
    {"title": "Cloud Container (PaaS)", "url": "https://docs.arvancloud.ir/en/cloud-container/", "tags": "paas kubernetes container deployment kubectl"},
    {"title": "Container CLI", "url": "https://docs.arvancloud.ir/en/developer-tools/cli/", "tags": "cli arvan paas kubeconfig"},
    {"title": "Changelog", "url": "https://docs.arvancloud.ir/en/changelog", "tags": "changelog updates releases"},
]


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == s or host.endswith("." + s) for s in _ALLOWED_HOST_SUFFIXES)


def _html_to_text(body: str) -> str:
    body = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", body)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    body = html.unescape(body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n\s*\n\s*\n+", "\n\n", body)
    return body.strip()


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_docs_topics() -> dict:
        """List curated ArvanCloud documentation topics and their URLs."""

        return {"topics": [{"title": d["title"], "url": d["url"]} for d in _DOC_INDEX]}

    @mcp.tool()
    async def arvan_docs_search(query: str, limit: int = 8) -> dict:
        """Search the curated ArvanCloud documentation index for a query."""

        terms = [t for t in re.split(r"\W+", query.lower()) if t]
        scored = []
        for d in _DOC_INDEX:
            haystack = f"{d['title']} {d['tags']}".lower()
            score = sum(haystack.count(t) for t in terms)
            if score:
                scored.append((score, d))
        scored.sort(key=lambda x: -x[0])
        results = [
            {"title": d["title"], "url": d["url"]} for _s, d in scored[: max(1, limit)]
        ]
        return {
            "query": query,
            "results": results,
            "site_search": f"https://docs.arvancloud.ir/en/search?q={query.replace(' ', '+')}",
            "hint": "Use arvan_docs_fetch(url) to read a page's content.",
        }

    @mcp.tool()
    async def arvan_docs_fetch(url: str, max_chars: int = _MAX_DOC_CHARS) -> dict:
        """Fetch an ArvanCloud documentation page and return it as plain text.

        Only ArvanCloud domains (arvancloud.ir / arvancloud.com) are allowed.
        """

        if not _host_allowed(url):
            return {
                "ok": False,
                "error": "only arvancloud.ir / arvancloud.com URLs are allowed; "
                "use arvan_docs_search to find one.",
            }
        try:
            async with httpx.AsyncClient(
                timeout=20.0, follow_redirects=True,
                headers={"User-Agent": client.settings.user_agent},
            ) as hc:
                resp = await hc.get(url)
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc), "url": url}
        if resp.status_code >= 400:
            return {"ok": False, "status_code": resp.status_code, "url": url}
        text = _html_to_text(resp.text)
        truncated = len(text) > max_chars
        return {
            "ok": True,
            "url": str(resp.url),
            "truncated": truncated,
            "content": text[:max_chars],
        }
