"""Security & hardening tools.

A mix of:
* Scanners that wrap open-source tools (degrade gracefully if not installed):
  gitleaks/trufflehog (secrets), trivy (vulns/misconfig/images), syft (SBOM),
  semgrep (SAST).
* Cloud-native, always-available checks built on the ArvanCloud API and stdlib:
  security-group auditing, HTTP security-header grading.
* Generators: strong passwords and SSH keypairs (handy for hardening servers
  before you create them).
"""

from __future__ import annotations

import secrets
import string
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._base import resolve_region
from ._exec import run_command, which
from ._exec import workspace as _workspace

_SEC_BINARIES = {
    "gitleaks": "gitleaks",
    "trufflehog": "trufflehog",
    "trivy": "trivy",
    "syft": "syft",
    "grype": "grype",
    "semgrep": "semgrep",
}

_SENSITIVE_PORTS = {
    22: "SSH", 23: "Telnet", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL",
    6379: "Redis", 27017: "MongoDB", 9200: "Elasticsearch", 5601: "Kibana",
    11211: "Memcached", 2375: "Docker", 2376: "Docker", 5672: "RabbitMQ",
    15672: "RabbitMQ-mgmt", 9092: "Kafka", 8086: "InfluxDB", 25: "SMTP",
}

_SECURITY_HEADERS = {
    "strict-transport-security": "HSTS (force HTTPS)",
    "content-security-policy": "Content-Security-Policy",
    "x-content-type-options": "X-Content-Type-Options (nosniff)",
    "x-frame-options": "X-Frame-Options (clickjacking)",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
}


def _is_world_open(cidr: str | None) -> bool:
    if not cidr:
        return True
    cidr = cidr.strip()
    return cidr in {"0.0.0.0/0", "::/0", "0.0.0.0", "*", "any"} or cidr.endswith("/0")


def register(mcp: FastMCP, client: ArvanClient) -> None:
    timeout = getattr(client.settings, "iac_timeout", 120.0)

    @mcp.tool()
    async def arvan_security_available_tools() -> Any:
        """Report which security scanners are installed (and their paths)."""

        return {
            name: {"installed": which(b) is not None, "path": which(b)}
            for name, b in _SEC_BINARIES.items()
        }

    @mcp.tool()
    async def arvan_security_scan_secrets(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Scan a directory/files for committed secrets with gitleaks."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                [
                    "gitleaks", "detect", "--source", workdir, "--no-git",
                    "--report-format", "json", "--report-path", "/dev/stdout",
                    "--redact",
                ],
                cwd=workdir,
                timeout=timeout,
            )

    @mcp.tool()
    async def arvan_security_scan_vulnerabilities(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Scan a filesystem for vulns, secrets and misconfig with Trivy (``trivy fs``)."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                ["trivy", "fs", "--format", "json", "--quiet", workdir],
                cwd=workdir,
                timeout=timeout,
            )

    @mcp.tool()
    async def arvan_security_scan_image(image: str) -> Any:
        """Scan a container image for vulnerabilities with Trivy (``trivy image``)."""

        return await run_command(
            ["trivy", "image", "--format", "json", "--quiet", image],
            timeout=max(timeout, 300.0),
        )

    @mcp.tool()
    async def arvan_security_generate_sbom(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        sbom_format: str = "syft-json",
    ) -> Any:
        """Generate a Software Bill of Materials (SBOM) with syft."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                ["syft", f"dir:{workdir}", "-o", sbom_format, "-q"],
                cwd=workdir,
                timeout=timeout,
            )

    @mcp.tool()
    async def arvan_security_grype(
        image: str | None = None,
        files: dict[str, str] | None = None,
        directory: str | None = None,
    ) -> Any:
        """Scan a container image or a directory for vulnerabilities with grype."""

        if image:
            return await run_command(
                ["grype", image, "-o", "json", "-q"], timeout=max(timeout, 300.0)
            )
        with _workspace(files, directory) as workdir:
            return await run_command(
                ["grype", f"dir:{workdir}", "-o", "json", "-q"],
                cwd=workdir, timeout=timeout,
            )

    @mcp.tool()
    async def arvan_security_sast(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        config: str = "auto",
    ) -> Any:
        """Static application security testing (SAST) with semgrep."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                ["semgrep", "--config", config, "--json", "--quiet", workdir],
                cwd=workdir,
                timeout=max(timeout, 300.0),
            )

    @mcp.tool()
    async def arvan_security_audit_security_groups(
        region: str | None = None,
    ) -> Any:
        """Audit ArvanCloud security groups for risky, world-open ingress rules.

        Flags inbound rules open to 0.0.0.0/0 (or ::/0) that expose sensitive
        ports (SSH, RDP, databases, …) or all ports. Returns findings with a
        severity so you can tighten them.
        """

        region = resolve_region(client, region)
        data = await client.request("GET", f"/ecc/v1/regions/{region}/securities")
        groups = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(groups, list):
            groups = []

        findings: list[dict[str, Any]] = []
        for grp in groups:
            if not isinstance(grp, dict):
                continue
            name = grp.get("name") or grp.get("id")
            for rule in grp.get("rules", []) or []:
                if not isinstance(rule, dict):
                    continue
                if (rule.get("direction") or "").lower() not in ("ingress", "incoming", ""):
                    continue
                cidr = rule.get("ip") or rule.get("ips")
                if isinstance(cidr, list):
                    open_to_world = any(_is_world_open(c) for c in cidr)
                else:
                    open_to_world = _is_world_open(cidr)
                if not open_to_world:
                    continue
                start = rule.get("port_start")
                end = rule.get("port_end")
                proto = (rule.get("protocol") or "any")
                if start in (None, 0, "0", "") and end in (None, 0, "65535", 65535, ""):
                    findings.append({
                        "security_group": name, "severity": "high",
                        "issue": "all ports open to the internet",
                        "protocol": proto, "source": cidr,
                    })
                    continue
                try:
                    s, e = int(start), int(end)
                except (TypeError, ValueError):
                    continue
                exposed = [p for p in _SENSITIVE_PORTS if s <= p <= e]
                for p in exposed:
                    findings.append({
                        "security_group": name, "severity": "high",
                        "issue": f"{_SENSITIVE_PORTS[p]} (port {p}) open to the internet",
                        "protocol": proto, "source": cidr,
                        "port_range": f"{s}-{e}",
                    })

        return {
            "region": region,
            "security_groups_checked": len(groups),
            "findings": findings,
            "ok": not findings,
            "summary": f"{len(findings)} risky rule(s) found" if findings else "no world-open sensitive rules found",
        }

    @mcp.tool()
    async def arvan_security_http_headers(url: str, timeout_s: float = 10.0) -> Any:
        """Check a URL's HTTP security headers and grade them."""

        try:
            async with httpx.AsyncClient(
                timeout=timeout_s, follow_redirects=True, verify=client.settings.verify_ssl
            ) as hc:
                resp = await hc.get(url)
        except httpx.HTTPError as exc:
            return {"url": url, "error": str(exc)}

        headers = {k.lower(): v for k, v in resp.headers.items()}
        present, missing = {}, []
        for key, label in _SECURITY_HEADERS.items():
            if key in headers:
                present[key] = headers[key]
            else:
                missing.append(label)
        score = len(present)
        total = len(_SECURITY_HEADERS)
        grade = ["F", "E", "D", "C", "B", "A", "A+"][min(score, total)]
        return {
            "url": url,
            "status_code": resp.status_code,
            "present": present,
            "missing": missing,
            "score": f"{score}/{total}",
            "grade": grade,
            "discloses_server": headers.get("server"),
        }

    @mcp.tool()
    async def arvan_security_generate_password(
        length: int = 24, include_symbols: bool = True
    ) -> Any:
        """Generate a cryptographically strong random password."""

        length = max(8, min(length, 256))
        alphabet = string.ascii_letters + string.digits
        if include_symbols:
            alphabet += "!@#$%^&*()-_=+[]{}"
        while True:
            pw = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                    and any(c.isdigit() for c in pw)):
                break
        return {"password": pw, "length": length}

    @mcp.tool()
    async def arvan_security_generate_ssh_keypair(
        key_type: str = "ed25519", comment: str = "arvancloud-mcp", bits: int = 4096
    ) -> Any:
        """Generate an SSH keypair (ed25519 or rsa) for provisioning servers.

        Returns the OpenSSH private key and the public key. Register the public
        key with ``arvan_create_ssh_key`` and pass the private key to the
        ``arvan_ssh_*`` tools.
        """

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

        key: Any
        if key_type.lower() == "rsa":
            key = rsa.generate_private_key(public_exponent=65537, key_size=max(2048, min(bits, 8192)))
        else:
            key = ed25519.Ed25519PrivateKey.generate()
            key_type = "ed25519"

        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        public_openssh = key.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode("ascii")
        if comment:
            public_openssh = f"{public_openssh} {comment}"
        return {
            "key_type": key_type,
            "private_key": private_pem,
            "public_key": public_openssh,
        }
