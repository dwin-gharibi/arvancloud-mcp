"""Configuration for the ArvanCloud MCP server.

All settings can be provided through environment variables so the server is
trivial to configure in a container or any deployment platform.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from . import __version__

DEFAULT_BASE_URL = "https://napi.arvancloud.ir"

ALL_SERVICES: tuple[str, ...] = (
    "common",
    "compute",
    "network",
    "storage",
    "objectstorage",
    "cdn",
    "dns",
    "vod",
    "live",
    "ssh",
    "provision",
    "k8s",
    "net",
    "iac",
    "security",
    "git",
    "tasks",
    "notify",
    "observability",
    "docs",
)

ALWAYS_ON: tuple[str, ...] = ("common", "observability")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _csv(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _parse_services(raw: str | None) -> tuple[str, ...]:
    if not raw or raw.strip().lower() in {"all", "*"}:
        return ALL_SERVICES
    requested = {part.strip().lower() for part in raw.split(",") if part.strip()}
    selected = [svc for svc in ALL_SERVICES if svc in requested]
    for svc in reversed(ALWAYS_ON):
        if svc not in selected:
            selected.insert(0, svc)
    return tuple(selected)


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the server and API client."""

    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 60.0
    max_retries: int = 4
    backoff_factor: float = 1.0
    default_region: str | None = None
    enabled_services: tuple[str, ...] = field(default_factory=lambda: ALL_SERVICES)
    verify_ssl: bool = True
    user_agent: str = f"arvancloud-mcp/{__version__}"

    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000

    stateless_http: bool = False
    json_response: bool = False

    iac_timeout: float = 120.0
    task_webhook: str = ""
    task_max_concurrency: int = 20
    task_max_tasks: int = 1000

    read_only: bool = False
    tools_allow: tuple[str, ...] = ()
    tools_deny: tuple[str, ...] = ()
    rate_limit_per_min: int = 0
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "ir-thr-at1"
    s3_endpoint: str = ""
    ssh_user: str = "root"
    ssh_key: str = ""
    ssh_key_file: str = ""
    ssh_password: str = ""
    ssh_port: int = 22
    ssh_known_hosts: str = ""
    ssh_timeout: float = 30.0

    def s3_endpoint_url(self) -> str:
        """The S3 endpoint, derived from the region when not set explicitly."""

        if self.s3_endpoint:
            return self.s3_endpoint.rstrip("/")
        return f"https://s3.{self.s3_region}.arvanstorage.ir"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables.

        Recognised variables:

        * ``ARVAN_API_KEY`` / ``ARVANCLOUD_API_KEY`` — machine-user access key.
        * ``ARVAN_BASE_URL`` — override the API host.
        * ``ARVAN_TIMEOUT`` — request timeout in seconds.
        * ``ARVAN_MAX_RETRIES`` — retry attempts for transient failures.
        * ``ARVAN_BACKOFF_FACTOR`` — exponential backoff base in seconds.
        * ``ARVAN_DEFAULT_REGION`` — default IaaS region (e.g. ``ir-thr-c2``).
        * ``ARVAN_ENABLED_SERVICES`` — comma list or ``all``.
        * ``ARVAN_VERIFY_SSL`` — set to ``false`` to disable TLS verification.
        * ``ARVAN_TRANSPORT`` — ``stdio`` (default), ``sse`` or ``streamable-http``.
        * ``ARVAN_HOST`` / ``ARVAN_PORT`` — bind address for HTTP transports.
        """

        api_key = (
            os.getenv("ARVAN_API_KEY")
            or os.getenv("ARVANCLOUD_API_KEY")
            or os.getenv("ARVAN_TOKEN")
            or ""
        ).strip()

        base_url = (os.getenv("ARVAN_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")

        transport = (os.getenv("ARVAN_TRANSPORT") or "stdio").strip().lower()
        if transport not in {"stdio", "sse", "streamable-http"}:
            transport = "stdio"

        return cls(
            api_key=api_key,
            base_url=base_url,
            timeout=_env_float("ARVAN_TIMEOUT", 60.0),
            max_retries=_env_int("ARVAN_MAX_RETRIES", 4),
            backoff_factor=_env_float("ARVAN_BACKOFF_FACTOR", 1.0),
            default_region=(os.getenv("ARVAN_DEFAULT_REGION") or "").strip() or None,
            enabled_services=_parse_services(os.getenv("ARVAN_ENABLED_SERVICES")),
            verify_ssl=_env_bool("ARVAN_VERIFY_SSL", True),
            transport=transport,
            host=(os.getenv("ARVAN_HOST") or "127.0.0.1").strip(),
            port=_env_int("ARVAN_PORT", 8000),
            s3_access_key=(os.getenv("ARVAN_S3_ACCESS_KEY") or "").strip(),
            s3_secret_key=(os.getenv("ARVAN_S3_SECRET_KEY") or "").strip(),
            s3_region=(os.getenv("ARVAN_S3_REGION") or "ir-thr-at1").strip(),
            s3_endpoint=(os.getenv("ARVAN_S3_ENDPOINT") or "").strip(),
            ssh_user=(os.getenv("ARVAN_SSH_USER") or "root").strip(),
            ssh_key=os.getenv("ARVAN_SSH_KEY") or "",
            ssh_key_file=(os.getenv("ARVAN_SSH_KEY_FILE") or "").strip(),
            ssh_password=os.getenv("ARVAN_SSH_PASSWORD") or "",
            ssh_port=_env_int("ARVAN_SSH_PORT", 22),
            ssh_known_hosts=(os.getenv("ARVAN_SSH_KNOWN_HOSTS") or "").strip(),
            ssh_timeout=_env_float("ARVAN_SSH_TIMEOUT", 30.0),
            stateless_http=_env_bool("ARVAN_STATELESS_HTTP", False),
            json_response=_env_bool("ARVAN_JSON_RESPONSE", False),
            iac_timeout=_env_float("ARVAN_IAC_TIMEOUT", 120.0),
            task_webhook=(os.getenv("ARVAN_TASK_WEBHOOK") or "").strip(),
            task_max_concurrency=_env_int("ARVAN_TASK_MAX_CONCURRENCY", 20),
            task_max_tasks=_env_int("ARVAN_TASK_MAX_TASKS", 1000),
            read_only=_env_bool("ARVAN_READ_ONLY", False),
            tools_allow=_csv(os.getenv("ARVAN_TOOLS_ALLOW")),
            tools_deny=_csv(os.getenv("ARVAN_TOOLS_DENY")),
            rate_limit_per_min=_env_int("ARVAN_RATE_LIMIT", 0),
        )

    def is_enabled(self, service: str) -> bool:
        return service in self.enabled_services
