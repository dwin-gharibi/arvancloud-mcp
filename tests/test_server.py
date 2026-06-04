"""Integration tests: build the server, list tools, and invoke them end-to-end."""

from __future__ import annotations

import json

import httpx
import respx

from arvancloud_mcp.catalog import CATALOG, summary
from arvancloud_mcp.server import build_server

from .conftest import TEST_BASE_URL, make_settings, unwrap


async def test_all_services_register_expected_tools():
    mcp, _client = build_server(make_settings())
    tools = await mcp.list_tools()
    names = {t.name for t in tools}

    expected = {
        "arvan_request",
        "arvan_capabilities",
        "arvan_doctor",
        "arvan_git_clone",
        "arvan_list_regions",
        "arvan_create_server",
        "arvan_server_action",
        "arvan_wait_for_server",
        "arvan_list_ssh_keys",
        "arvan_create_ssh_key",
        "arvan_list_tags",
        "arvan_list_security_groups",
        "arvan_create_floating_ip",
        "arvan_create_volume",
        "arvan_list_domains",
        "arvan_create_a_record",
        "arvan_set_dnssec",
        "arvan_create_rate_limit_rule",
        "arvan_list_log_forwarders",
        "arvan_create_cdn_app",
        "arvan_delete_floating_ip",
        "arvan_attach_security_group_to_server",
        "arvan_vod_list_channels",
        "arvan_vod_create_watermark",
        "arvan_live_list_channels",
        "arvan_s3_list_buckets",
        "arvan_s3_put_object",
        "arvan_ssh_run",
        "arvan_ssh_run_script",
        "arvan_provision_server",
        "arvan_k8s_apply",
        "arvan_kubectl",
        "arvan_helm_install",
        "arvan_net_http_check",
        "arvan_net_dns_lookup",
        "arvan_iac_available_tools",
        "arvan_iac_terraform_validate",
        "arvan_iac_terraform_apply",
        "arvan_security_generate_ssh_keypair",
        "arvan_security_audit_security_groups",
        "arvan_security_scan_vulnerabilities",
        "arvan_task_submit",
        "arvan_task_status",
        "arvan_task_cancel",
        "arvan_metrics",
        "arvan_audit_log",
        "arvan_notify_slack",
        "arvan_notify_webhook",
        "arvan_s3_sync_local_dir",
        "arvan_s3_enable_static_website",
        "arvan_ansible_playbook",
        "arvan_iac_terraform_cost",
        "arvan_docs_search",
        "arvan_docs_fetch",
        "arvan_find_tool",
        "arvan_iac_tfsec",
        "arvan_iac_opentofu_validate",
        "arvan_security_grype",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"
    assert len(names) >= 230


async def test_capabilities_resource_registered():
    mcp, _client = build_server(make_settings())
    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "arvan://capabilities" in uris


async def test_disabling_services_reduces_tool_surface():
    full, _ = build_server(make_settings())
    minimal, _ = build_server(make_settings(enabled_services=("common",)))

    full_names = {t.name for t in await full.list_tools()}
    minimal_names = {t.name for t in await minimal.list_tools()}

    assert "arvan_request" in minimal_names
    assert "arvan_capabilities" in minimal_names
    assert "arvan_list_servers" not in minimal_names
    assert minimal_names < full_names


async def test_list_servers_uses_default_region():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.get("/ecc/v1/regions/ir-thr-c2/servers").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        await mcp.call_tool("arvan_list_servers", {})
    assert route.called


async def test_server_action_hits_correct_path():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post(
            "/ecc/v1/regions/ir-thr-c2/servers/abc/power-off"
        ).mock(return_value=httpx.Response(200, json={"data": "ok"}))
        await mcp.call_tool(
            "arvan_server_action", {"server_id": "abc", "action": "power-off"}
        )
    assert route.called


async def test_create_a_record_builds_value_payload():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/cdn/4.0/domains/example.com/dns-records").mock(
            return_value=httpx.Response(201, json={"data": {"id": "1"}})
        )
        await mcp.call_tool(
            "arvan_create_a_record",
            {"domain": "example.com", "name": "www", "ips": ["1.2.3.4", "5.6.7.8"]},
        )

    body = json.loads(route.calls.last.request.content)
    assert body["type"] == "a"
    assert body["name"] == "www"
    assert body["value"] == [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]


async def test_generic_request_tool_reaches_any_endpoint():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.get("/live/2.0/channels").mock(
            return_value=httpx.Response(200, json={"data": ["c1"]})
        )
        await mcp.call_tool(
            "arvan_request", {"method": "GET", "path": "/live/2.0/channels"}
        )
    assert route.called


async def test_create_security_rule_payload_and_path():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post(
            "/ecc/v1/regions/ir-thr-c2/securities/security-rules/grp1"
        ).mock(return_value=httpx.Response(201, json={"data": {}}))
        await mcp.call_tool(
            "arvan_create_security_rule",
            {
                "group_id": "grp1",
                "direction": "ingress",
                "protocol": "tcp",
                "port_from": "80",
                "port_to": "80",
                "ips": ["0.0.0.0/0"],
            },
        )
    body = json.loads(route.calls.last.request.content)
    assert body["direction"] == "ingress"
    assert body["protocol"] == "tcp"
    assert body["ips"] == ["0.0.0.0/0"]


async def test_create_domain_uses_dns_service_endpoint():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/cdn/4.0/domains/dns-service").mock(
            return_value=httpx.Response(201, json={"data": {"id": "1"}})
        )
        await mcp.call_tool("arvan_create_domain", {"domain": "example.com"})
    assert route.called
    assert json.loads(route.calls.last.request.content) == {"domain": "example.com"}


async def test_purge_cache_deletes_caching_with_body():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.delete("/cdn/4.0/domains/example.com/caching").mock(
            return_value=httpx.Response(200, json={"data": "ok"})
        )
        await mcp.call_tool(
            "arvan_purge_cache",
            {"domain": "example.com", "urls": ["https://example.com/a.js"]},
        )
    body = json.loads(route.calls.last.request.content)
    assert body["purge"] == "individual"
    assert body["purge_urls"] == ["https://example.com/a.js"]


async def test_update_ssl_settings_uses_ssl_path():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.patch("/cdn/4.0/domains/example.com/ssl").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        await mcp.call_tool(
            "arvan_update_ssl_settings",
            {"domain": "example.com", "ssl_type": "default"},
        )
    assert json.loads(route.calls.last.request.content) == {"ssl_type": "default"}


async def test_import_dns_zone_sends_multipart_file():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/cdn/4.0/domains/example.com/dns-records/import").mock(
            return_value=httpx.Response(200, json={"data": "ok"})
        )
        await mcp.call_tool(
            "arvan_import_dns_zone",
            {"domain": "example.com", "zone": "www 300 IN A 1.2.3.4"},
        )
    request = route.calls.last.request
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b"f_zone_file" in request.content
    assert b"1.2.3.4" in request.content


def test_catalog_summary_is_consistent_with_catalog():
    s = summary()
    assert s["base_url"] == CATALOG["base_url"]
    doc_only = {"iam", "container"}
    for key, svc in CATALOG["services"].items():
        if key in doc_only:
            continue
        assert svc["endpoints"], f"service {key} has no endpoints"
    for key in ("objectstorage", "ssh", "live"):
        assert key in CATALOG["services"]


async def test_create_ssh_key_payload():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/ecc/v1/regions/ir-thr-c2/ssh-keys").mock(
            return_value=httpx.Response(201, json={"data": {"name": "k1"}})
        )
        await mcp.call_tool(
            "arvan_create_ssh_key",
            {"name": "k1", "public_key": "ssh-ed25519 AAAA..."},
        )
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "k1", "public_key": "ssh-ed25519 AAAA..."}


async def test_rate_limit_rule_path():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/cdn/4.0/domains/example.com/rate-limit/rules").mock(
            return_value=httpx.Response(201, json={"data": {}})
        )
        await mcp.call_tool(
            "arvan_create_rate_limit_rule",
            {"domain": "example.com", "rule": {"url": "/*", "count": 100}},
        )
    assert route.called


async def test_wait_for_server_returns_when_active():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        mock.get("/ecc/v1/regions/ir-thr-c2/servers/s1").mock(
            return_value=httpx.Response(200, json={"data": {"id": "s1", "status": "ACTIVE"}})
        )
        result = unwrap(
            await mcp.call_tool("arvan_wait_for_server", {"server_id": "s1"})
        )
    assert result["ready"] is True
    assert result["status"] == "ACTIVE"


async def test_live_create_channel_payload():
    mcp, _client = build_server(make_settings())
    async with respx.mock(base_url=TEST_BASE_URL) as mock:
        route = mock.post("/live/2.0/channels").mock(
            return_value=httpx.Response(201, json={"data": {"id": "c1"}})
        )
        await mcp.call_tool(
            "arvan_live_create_channel",
            {"title": "My Stream", "extra": {"archive_enabled": True}},
        )
    body = json.loads(route.calls.last.request.content)
    assert body["title"] == "My Stream"
    assert body["archive_enabled"] is True
