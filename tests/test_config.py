"""Tests for environment-driven configuration."""

from __future__ import annotations

from arvancloud_mcp.config import ALL_SERVICES, Settings


def test_all_services_includes_new_groups():
    for svc in (
        "objectstorage", "ssh", "live", "provision", "k8s", "net", "iac",
        "security", "git", "tasks", "notify", "observability", "docs",
    ):
        assert svc in ALL_SERVICES
    assert ALL_SERVICES[0] == "common"


def test_from_env_defaults(monkeypatch):
    for var in (
        "ARVAN_API_KEY", "ARVANCLOUD_API_KEY", "ARVAN_TOKEN", "ARVAN_BASE_URL",
        "ARVAN_ENABLED_SERVICES", "ARVAN_TRANSPORT", "ARVAN_DEFAULT_REGION",
    ):
        monkeypatch.delenv(var, raising=False)
    s = Settings.from_env()
    assert s.base_url == "https://napi.arvancloud.ir"
    assert s.transport == "stdio"
    assert s.enabled_services == ALL_SERVICES


def test_from_env_reads_all_settings(monkeypatch):
    monkeypatch.setenv("ARVAN_API_KEY", "Apikey abc")
    monkeypatch.setenv("ARVAN_DEFAULT_REGION", "ir-tbz-dc1")
    monkeypatch.setenv("ARVAN_ENABLED_SERVICES", "compute, ssh, objectstorage")
    monkeypatch.setenv("ARVAN_S3_ACCESS_KEY", "ak")
    monkeypatch.setenv("ARVAN_S3_SECRET_KEY", "sk")
    monkeypatch.setenv("ARVAN_S3_REGION", "ir-tbz-sh1")
    monkeypatch.setenv("ARVAN_SSH_USER", "ubuntu")
    monkeypatch.setenv("ARVAN_SSH_PORT", "2200")
    monkeypatch.setenv("ARVAN_TRANSPORT", "streamable-http")
    monkeypatch.setenv("ARVAN_PORT", "9000")
    monkeypatch.setenv("ARVAN_STATELESS_HTTP", "true")
    monkeypatch.setenv("ARVAN_JSON_RESPONSE", "true")
    monkeypatch.setenv("ARVAN_IAC_TIMEOUT", "200")

    s = Settings.from_env()
    assert s.api_key == "Apikey abc"
    assert s.default_region == "ir-tbz-dc1"
    assert s.enabled_services == (
        "common", "observability", "compute", "objectstorage", "ssh",
    )
    assert s.s3_access_key == "ak" and s.s3_secret_key == "sk"
    assert s.s3_endpoint_url() == "https://s3.ir-tbz-sh1.arvanstorage.ir"
    assert s.ssh_user == "ubuntu" and s.ssh_port == 2200
    assert s.transport == "streamable-http" and s.port == 9000
    assert s.stateless_http is True and s.json_response is True
    assert s.iac_timeout == 200.0


def test_invalid_transport_falls_back_to_stdio(monkeypatch):
    monkeypatch.setenv("ARVAN_TRANSPORT", "carrier-pigeon")
    assert Settings.from_env().transport == "stdio"


def test_is_enabled():
    s = Settings(enabled_services=("common", "compute"))
    assert s.is_enabled("compute")
    assert not s.is_enabled("vod")
