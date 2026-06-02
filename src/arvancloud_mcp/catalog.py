"""A machine-readable catalogue of the ArvanCloud API surface.

This powers the ``arvan_capabilities`` tool and the ``arvan://capabilities``
resource. It lets an MCP client discover every product and endpoint — including
ones that do not have a dedicated typed tool — so they can be reached through
the generic ``arvan_request`` tool.

Paths are templates relative to the API base URL. Placeholders in braces
(``{region}``, ``{domain}``, ``{id}`` …) must be substituted before calling.
"""

from __future__ import annotations

from typing import Any

KNOWN_REGIONS: list[dict[str, str]] = [
    {"code": "ir-thr-c2", "name": "Tehran — Forough datacenter"},
    {"code": "ir-thr-c1", "name": "Tehran — Simin datacenter"},
    {"code": "ir-thr-w1", "name": "Tehran — West"},
    {"code": "ir-tbz-dc1", "name": "Tabriz — Shahriar datacenter"},
    {"code": "ir-thr-at1", "name": "Tehran — Asiatech"},
    {"code": "nl-ams-dc1", "name": "Amsterdam (international)"},
]

CATALOG: dict[str, Any] = {
    "base_url": "https://napi.arvancloud.ir",
    "auth": {
        "header": "Authorization",
        "format": "Apikey <machine-user-access-key>",
        "note": "Create a machine user and access key in the ArvanCloud panel "
        "(Settings -> Machine User / API keys). The capital 'A' in 'Apikey' "
        "matters. The server adds the 'Apikey ' prefix automatically.",
    },
    "regions": KNOWN_REGIONS,
    "services": {
        "compute": {
            "title": "Cloud Server (IaaS / Abrak)",
            "base_path": "/ecc/v1",
            "docs": "https://docs.arvancloud.ir/en/developer-tools/api/",
            "summary": "Virtual machines, images, plans, quotas and server actions.",
            "endpoints": [
                {"method": "GET", "path": "/ecc/v1/regions", "summary": "List regions"},
                {"method": "GET", "path": "/ecc/v1/details", "summary": "Account / project details"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/quotas", "summary": "Resource quotas"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/servers", "summary": "List servers"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers", "summary": "Create server"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/servers/{id}", "summary": "Get server"},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/servers/{id}", "summary": "Delete server"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/servers/options", "summary": "Server creation options"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/power-on", "summary": "Power on"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/power-off", "summary": "Power off"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/reboot", "summary": "Soft reboot"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/hard-reboot", "summary": "Hard reboot"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/rescue", "summary": "Enter rescue mode"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/unrescue", "summary": "Exit rescue mode"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/rename", "summary": "Rename server", "body": {"name": "str"}},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/rebuild", "summary": "Rebuild from image", "body": {"image_id": "str"}},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/resize", "summary": "Change flavor", "body": {"flavor_id": "str"}},
                {"method": "PUT", "path": "/ecc/v1/regions/{region}/servers/{id}/resizeRoot", "summary": "Resize root disk", "body": {"size": "int"}},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/reset-root-password", "summary": "Reset root password"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/add-public-ip", "summary": "Add public IP"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/change-public-ip", "summary": "Change public IP"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/add-security-group", "summary": "Attach security group"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/servers/{id}/remove-security-group", "summary": "Detach security group"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/images", "summary": "List images"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/images/marketplace", "summary": "Marketplace images"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/sizes", "summary": "List plans / flavors"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/ptr", "summary": "List PTR records"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/ptr", "summary": "Create PTR record", "body": {"ip": "str", "domain": "str"}},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/ptr/{id}", "summary": "Delete PTR record"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/tags", "summary": "List tags"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/tags", "summary": "Create tag"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/ssh-keys", "summary": "List SSH keys"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/ssh-keys", "summary": "Create SSH key", "body": {"name": "str", "public_key": "str"}},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/ssh-keys/{name}", "summary": "Delete SSH key"},
            ],
        },
        "network": {
            "title": "Cloud Networking",
            "base_path": "/ecc/v1",
            "docs": "https://docs.arvancloud.ir/en/cloud-server/",
            "summary": "Private networks, subnets, security groups, floating IPs and ports.",
            "endpoints": [
                {"method": "GET", "path": "/ecc/v1/regions/{region}/networks", "summary": "List networks"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/subnets", "summary": "List subnets"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/subnets", "summary": "Create private network/subnet"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/subnets/{id}", "summary": "Get subnet"},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/subnets/{id}", "summary": "Update subnet"},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/subnets/{id}", "summary": "Delete subnet"},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/networks/{id}/attach", "summary": "Attach network to server", "body": {"server_id": "str", "ip": "str"}},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/networks/{id}/detach", "summary": "Detach network from server", "body": {"server_id": "str"}},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/securities", "summary": "List security groups"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/securities", "summary": "Create security group", "body": {"name": "str", "description": "str"}},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/securities/{id}", "summary": "Delete security group"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/securities/security-rules/{group_id}", "summary": "Create security rule", "body": {"direction": "ingress|egress", "protocol": "tcp|udp|...", "port_from": "str", "port_to": "str", "ips": "[str]"}},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/securities/security-rules/{id}", "summary": "Delete security rule"},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/float-ips", "summary": "List floating IPs"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/float-ips", "summary": "Create floating IP", "body": {"description": "str"}},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/float-ip/{id}/attach", "summary": "Attach floating IP", "body": {"server_id": "str", "subnet_id": "str", "port_id": "str"}},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/float-ip/detach", "summary": "Detach floating IP", "body": {"port_id": "str"}},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/float-ips/{id}", "summary": "Release floating IP"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/ports/{id}/enable", "summary": "Enable port security"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/ports/{id}/disable", "summary": "Disable port security"},
            ],
        },
        "storage": {
            "title": "Block Storage & Object Storage",
            "base_path": "/ecc/v1",
            "docs": "https://docs.arvancloud.ir/en/cloud-storage/",
            "summary": "Block volumes and snapshots. Object storage is S3-compatible "
            "and is accessed through the S3 API (see notes), not this server's typed tools.",
            "endpoints": [
                {"method": "GET", "path": "/ecc/v1/regions/{region}/volumes", "summary": "List volumes"},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/volumes", "summary": "Create volume", "body": {"name": "str", "size": "int(GB)", "description": "str"}},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/volumes/{id}", "summary": "Get volume"},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/volumes/{id}", "summary": "Update volume"},
                {"method": "DELETE", "path": "/ecc/v1/regions/{region}/volumes/{id}", "summary": "Delete volume"},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/volumes/attach", "summary": "Attach volume", "body": {"server_id": "str", "volume_id": "str"}},
                {"method": "PATCH", "path": "/ecc/v1/regions/{region}/volumes/detach", "summary": "Detach volume", "body": {"server_id": "str", "volume_id": "str"}},
                {"method": "POST", "path": "/ecc/v1/regions/{region}/volumes/{id}/snapshot", "summary": "Snapshot volume", "body": {"name": "str", "description": "str"}},
                {"method": "GET", "path": "/ecc/v1/regions/{region}/volumes/limits", "summary": "Volume limits"},
            ],
            "notes": [
                "Object Storage uses an S3-compatible API at "
                "https://s3.<region>.arvanstorage.ir with separate access/secret "
                "keys. Use an S3 client (e.g. boto3) for bucket/object operations.",
            ],
        },
        "cdn": {
            "title": "CDN & Cloud Security",
            "base_path": "/cdn/4.0",
            "docs": "https://docs.arvancloud.ir/en/cdn/",
            "summary": "Domains, caching, page rules, firewall/WAF, HTTPS and CDN apps.",
            "endpoints": [
                {"method": "GET", "path": "/cdn/4.0/domains", "summary": "List domains"},
                {"method": "POST", "path": "/cdn/4.0/domains/dns-service", "summary": "Add domain", "body": {"domain": "str"}},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}", "summary": "Get domain"},
                {"method": "DELETE", "path": "/cdn/4.0/domains/{domain}?id={id}", "summary": "Delete domain (needs domain id)"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/caching", "summary": "Get caching settings"},
                {"method": "PATCH", "path": "/cdn/4.0/domains/{domain}/caching", "summary": "Update caching settings"},
                {"method": "DELETE", "path": "/cdn/4.0/domains/{domain}/caching", "summary": "Purge cache", "body": {"purge": "all|individual", "purge_urls": "[str]"}},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/page-rules", "summary": "List page rules"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/page-rules", "summary": "Create page rule"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/firewall/rules", "summary": "List firewall rules"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/firewall/rules", "summary": "Create firewall rule"},
                {"method": "DELETE", "path": "/cdn/4.0/domains/{domain}/firewall/rules/{id}", "summary": "Delete firewall rule"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/rate-limit/rules", "summary": "List rate-limit rules"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/rate-limit/rules", "summary": "Create rate-limit rule"},
                {"method": "DELETE", "path": "/cdn/4.0/domains/{domain}/rate-limit/rules/{id}", "summary": "Delete rate-limit rule"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/log-forwarders", "summary": "List log forwarders"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/log-forwarders", "summary": "Create log forwarder"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/metric-exporters", "summary": "List metric exporters"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/metric-exporters", "summary": "Create metric exporter"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/reports", "summary": "Traffic/analytics reports (params vary)"},
                {"method": "GET", "path": "/cdn/4.0/ip-lists", "summary": "Account-level IP lists (reusable across domains)"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/ssl", "summary": "Get HTTPS/SSL settings"},
                {"method": "PATCH", "path": "/cdn/4.0/domains/{domain}/ssl", "summary": "Update HTTPS/SSL settings", "body": {"ssl_type": "default|manual|off"}},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/apps", "summary": "List CDN apps"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/apps", "summary": "Create CDN app"},
            ],
        },
        "dns": {
            "title": "Cloud DNS",
            "base_path": "/cdn/4.0",
            "docs": "https://docs.arvancloud.ir/en/cdn/dns-records/",
            "summary": "DNS records, DNSSEC and zone import. Record types: a, aaaa, "
            "cname, mx, txt, ns, srv, spf, ptr, tlsa, caa, aname, dkim.",
            "endpoints": [
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/dns-records", "summary": "List DNS records"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/dns-records", "summary": "Create DNS record", "body": {"type": "a|aaaa|cname|mx|txt|...", "name": "str", "value": "object", "ttl": "int", "cloud": "bool"}},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/dns-records/{id}", "summary": "Get DNS record"},
                {"method": "PUT", "path": "/cdn/4.0/domains/{domain}/dns-records/{id}", "summary": "Update DNS record"},
                {"method": "DELETE", "path": "/cdn/4.0/domains/{domain}/dns-records/{id}", "summary": "Delete DNS record"},
                {"method": "PUT", "path": "/cdn/4.0/domains/{domain}/dns-records/{id}/cloud", "summary": "Toggle cloud (proxy) for record"},
                {"method": "POST", "path": "/cdn/4.0/domains/{domain}/dns-records/import", "summary": "Import zone file"},
                {"method": "GET", "path": "/cdn/4.0/domains/{domain}/dnssec", "summary": "Get DNSSEC status"},
                {"method": "PUT", "path": "/cdn/4.0/domains/{domain}/dnssec/actions", "summary": "Enable/disable DNSSEC"},
            ],
        },
        "vod": {
            "title": "Video on Demand (VOD)",
            "base_path": "/vod/2.0",
            "docs": "https://docs.arvancloud.ir/en/video-platform/",
            "summary": "Channels, videos, audios, subtitles, watermarks and profiles.",
            "endpoints": [
                {"method": "GET", "path": "/vod/2.0/channels", "summary": "List channels"},
                {"method": "POST", "path": "/vod/2.0/channels", "summary": "Create channel", "body": {"title": "str", "description": "str"}},
                {"method": "GET", "path": "/vod/2.0/channels/{channel_id}", "summary": "Get channel"},
                {"method": "PATCH", "path": "/vod/2.0/channels/{channel_id}", "summary": "Update channel"},
                {"method": "DELETE", "path": "/vod/2.0/channels/{channel_id}", "summary": "Delete channel"},
                {"method": "GET", "path": "/vod/2.0/channels/{channel_id}/videos", "summary": "List videos"},
                {"method": "POST", "path": "/vod/2.0/channels/{channel_id}/videos", "summary": "Create video"},
                {"method": "GET", "path": "/vod/2.0/videos/{video_id}", "summary": "Get video"},
                {"method": "PATCH", "path": "/vod/2.0/videos/{video_id}", "summary": "Update video"},
                {"method": "DELETE", "path": "/vod/2.0/videos/{video_id}", "summary": "Delete video"},
                {"method": "GET", "path": "/vod/2.0/channels/{channel_id}/audios", "summary": "List audios"},
                {"method": "POST", "path": "/vod/2.0/channels/{channel_id}/audios", "summary": "Create audio"},
                {"method": "GET", "path": "/vod/2.0/videos/{video_id}/subtitles", "summary": "List subtitles"},
                {"method": "POST", "path": "/vod/2.0/videos/{video_id}/subtitles", "summary": "Create subtitle"},
                {"method": "GET", "path": "/vod/2.0/channels/{channel_id}/watermarks", "summary": "List watermarks"},
                {"method": "GET", "path": "/vod/2.0/channels/{channel_id}/profiles", "summary": "List profiles"},
            ],
        },
        "live": {
            "title": "Live Streaming",
            "base_path": "/live/2.0",
            "docs": "https://docs.arvancloud.ir/en/vod/live/",
            "summary": "Live channels (push/pull URLs, stream keys) and inputs.",
            "endpoints": [
                {"method": "GET", "path": "/live/2.0/channels", "summary": "List live channels"},
                {"method": "POST", "path": "/live/2.0/channels", "summary": "Create live channel"},
                {"method": "GET", "path": "/live/2.0/channels/{channel_id}", "summary": "Get live channel"},
                {"method": "PATCH", "path": "/live/2.0/channels/{channel_id}", "summary": "Update live channel"},
                {"method": "DELETE", "path": "/live/2.0/channels/{channel_id}", "summary": "Delete live channel"},
                {"method": "GET", "path": "/live/2.0/channels/{channel_id}/inputs", "summary": "List channel inputs"},
            ],
        },
        "objectstorage": {
            "title": "Object Storage (S3-compatible)",
            "base_path": "https://s3.<region>.arvanstorage.ir",
            "docs": "https://docs.arvancloud.ir/en/developer-tools/sdk/object-storage/",
            "summary": "Buckets and objects over the S3 API. Uses its own "
            "access/secret key (ARVAN_S3_ACCESS_KEY/ARVAN_S3_SECRET_KEY), not the "
            "machine-user API key. Tools are prefixed arvan_s3_*.",
            "endpoints": [
                {"method": "S3", "path": "ListBuckets", "summary": "arvan_s3_list_buckets"},
                {"method": "S3", "path": "CreateBucket/DeleteBucket", "summary": "arvan_s3_create_bucket / delete_bucket"},
                {"method": "S3", "path": "ListObjectsV2", "summary": "arvan_s3_list_objects"},
                {"method": "S3", "path": "PutObject/GetObject/DeleteObject", "summary": "arvan_s3_put_object / get_object / delete_object"},
                {"method": "S3", "path": "CopyObject/HeadObject", "summary": "arvan_s3_copy_object / head_object"},
                {"method": "S3", "path": "PresignedURL", "summary": "arvan_s3_generate_presigned_url"},
                {"method": "S3", "path": "Bucket policy/ACL", "summary": "arvan_s3_get/put_bucket_policy, set_bucket_acl"},
            ],
            "regions": [
                {"endpoint": "https://s3.ir-thr-at1.arvanstorage.ir", "name": "Simin (Tehran)"},
                {"endpoint": "https://s3.ir-tbz-sh1.arvanstorage.ir", "name": "Shahriar (Tabriz)"},
            ],
        },
        "ssh": {
            "title": "Remote execution (SSH/SFTP)",
            "base_path": "(direct SSH to your servers)",
            "docs": "https://docs.arvancloud.ir/en/cloud-server/",
            "summary": "Provision a server, then SSH in to run commands and transfer "
            "files. Tools: arvan_ssh_run, arvan_ssh_run_script, arvan_ssh_upload_file, "
            "arvan_ssh_download_file, arvan_ssh_check_connection. Defaults from "
            "ARVAN_SSH_USER/ARVAN_SSH_KEY(_FILE)/ARVAN_SSH_PASSWORD.",
            "endpoints": [
                {"method": "SSH", "path": "exec", "summary": "arvan_ssh_run / arvan_ssh_run_script"},
                {"method": "SFTP", "path": "put/get", "summary": "arvan_ssh_upload_file / arvan_ssh_download_file"},
                {"method": "SSH", "path": "connect", "summary": "arvan_ssh_check_connection"},
            ],
        },
        "provision": {
            "title": "One-call provisioning",
            "base_path": "(compute + ssh)",
            "docs": "https://docs.arvancloud.ir/en/cloud-server/",
            "summary": "arvan_provision_server: generate/register an SSH key, create "
            "a server, wait for boot, detect its public IP, then SSH in and install "
            "packages / Docker / run a setup script — all in one call.",
            "endpoints": [
                {"method": "ORCH", "path": "provision_server", "summary": "create + wait + install in one call"},
            ],
        },
        "k8s": {
            "title": "Kubernetes & Helm",
            "base_path": "(kubectl / helm)",
            "docs": "https://docs.arvancloud.ir/en/cloud-container/",
            "summary": "Deploy to any Kubernetes cluster (incl. ArvanCloud PaaS) with "
            "kubectl and Helm. Tools: arvan_k8s_apply/delete/get, arvan_kubectl, "
            "arvan_helm_install/uninstall. Pass a kubeconfig inline or by path.",
            "endpoints": [
                {"method": "K8S", "path": "apply / delete / get", "summary": "arvan_k8s_apply / delete / get"},
                {"method": "K8S", "path": "kubectl", "summary": "arvan_kubectl (generic)"},
                {"method": "HELM", "path": "install / uninstall", "summary": "arvan_helm_install / uninstall"},
            ],
        },
        "net": {
            "title": "Networking diagnostics",
            "base_path": "(local tools)",
            "docs": "",
            "summary": "DNS lookups, reverse DNS, TCP/port checks, HTTP checks, "
            "TLS certificate inspection, ping/traceroute/whois, and a concurrent "
            "HTTP load tester. Tools: arvan_net_*.",
            "endpoints": [
                {"method": "NET", "path": "dns_lookup / reverse_dns", "summary": "arvan_net_dns_lookup / reverse_dns"},
                {"method": "NET", "path": "tcp_check / port_scan", "summary": "arvan_net_tcp_check / port_scan"},
                {"method": "NET", "path": "http_check / http_load_test", "summary": "arvan_net_http_check / http_load_test"},
                {"method": "NET", "path": "tls_cert", "summary": "arvan_net_tls_cert"},
                {"method": "NET", "path": "ping / traceroute / whois / my_public_ip", "summary": "arvan_net_ping / traceroute / whois / my_public_ip"},
            ],
        },
        "iac": {
            "title": "IaC validation & linting",
            "base_path": "(local tools)",
            "docs": "",
            "summary": "Validate/lint infrastructure-as-code with open-source tools "
            "(terraform, tflint, checkov, kubeconform, kube-linter, hadolint, "
            "yamllint, trivy). Tools: arvan_iac_*. Run arvan_iac_available_tools "
            "to see what's installed.",
            "endpoints": [
                {"method": "IAC", "path": "terraform validate/fmt", "summary": "arvan_iac_terraform_validate / terraform_fmt"},
                {"method": "IAC", "path": "tflint / checkov / trivy", "summary": "arvan_iac_tflint / checkov / trivy_config"},
                {"method": "IAC", "path": "kubernetes validate/lint", "summary": "arvan_iac_validate_kubernetes / kube_linter"},
                {"method": "IAC", "path": "dockerfile / yaml lint", "summary": "arvan_iac_lint_dockerfile / lint_yaml"},
            ],
        },
        "security": {
            "title": "Security & hardening",
            "base_path": "(local + API)",
            "docs": "",
            "summary": "Secret/vuln/SBOM/SAST scanners (gitleaks, trivy, syft, "
            "semgrep), cloud security-group auditing, HTTP security-header "
            "grading, and password / SSH-keypair generators. Tools: arvan_security_*.",
            "endpoints": [
                {"method": "SEC", "path": "scan_secrets / scan_vulnerabilities / scan_image", "summary": "gitleaks / trivy fs / trivy image"},
                {"method": "SEC", "path": "generate_sbom / sast", "summary": "syft / semgrep"},
                {"method": "SEC", "path": "audit_security_groups", "summary": "flag world-open ingress on sensitive ports"},
                {"method": "SEC", "path": "http_headers", "summary": "grade HTTP security headers"},
                {"method": "SEC", "path": "generate_password / generate_ssh_keypair", "summary": "strong secrets for hardening"},
            ],
        },
        "docs": {
            "title": "Documentation search & reading",
            "base_path": "(docs.arvancloud.ir)",
            "docs": "https://docs.arvancloud.ir/en/",
            "summary": "Search a curated index of ArvanCloud docs and fetch pages as "
            "plain text. Tools: arvan_docs_search, arvan_docs_fetch, arvan_docs_topics.",
            "endpoints": [
                {"method": "DOCS", "path": "search / topics", "summary": "arvan_docs_search / arvan_docs_topics"},
                {"method": "DOCS", "path": "fetch", "summary": "arvan_docs_fetch (arvancloud domains only)"},
            ],
        },
        "notify": {
            "title": "Notifications",
            "base_path": "(Slack/Telegram/SMTP/webhook)",
            "docs": "",
            "summary": "Send messages to Slack, Telegram, a generic webhook, or email "
            "(SMTP). Tools: arvan_notify_slack / telegram / webhook / email.",
            "endpoints": [
                {"method": "NOTE", "path": "slack / telegram / webhook / email", "summary": "arvan_notify_*"},
            ],
        },
        "observability": {
            "title": "Observability & ops",
            "base_path": "(in-process)",
            "docs": "",
            "summary": "Tool-call metrics (JSON + Prometheus), an audit log of mutating "
            "calls, and optional per-minute rate limiting (ARVAN_RATE_LIMIT). Tools: "
            "arvan_metrics, arvan_audit_log.",
            "endpoints": [
                {"method": "OBS", "path": "metrics", "summary": "arvan_metrics (JSON or prometheus=true)"},
                {"method": "OBS", "path": "audit_log", "summary": "arvan_audit_log"},
            ],
        },
        "tasks": {
            "title": "Background tasks & scheduling",
            "base_path": "(in-process scheduler)",
            "docs": "",
            "summary": "Run any tool in the background, on a delay, or on a recurring "
            "interval; poll status/result; announce completion via webhook "
            "(ARVAN_TASK_WEBHOOK or per-task). Tools: arvan_task_submit / list / "
            "status / cancel.",
            "endpoints": [
                {"method": "TASK", "path": "submit", "summary": "arvan_task_submit (delay/interval/max_runs/webhook)"},
                {"method": "TASK", "path": "list / status / cancel", "summary": "arvan_task_list / status / cancel"},
            ],
        },
        "git": {
            "title": "Git",
            "base_path": "(git binary)",
            "docs": "",
            "summary": "Clone and inspect repositories — e.g. pull an IaC repo then "
            "validate/plan it. Tools: arvan_git_clone/status/log/diff/checkout/pull.",
            "endpoints": [
                {"method": "GIT", "path": "clone", "summary": "arvan_git_clone"},
                {"method": "GIT", "path": "status / log / diff / ls-files", "summary": "inspect a checkout"},
                {"method": "GIT", "path": "checkout / pull", "summary": "switch refs / update"},
            ],
        },
        "iam": {
            "title": "Identity & Access Management",
            "base_path": "(napi)",
            "docs": "https://docs.arvancloud.ir/en/cloud-server/iam/",
            "summary": "Machine users, access keys, resource groups and roles. Manage "
            "via the panel or the generic arvan_request tool; access keys created "
            "here are what this server authenticates with.",
            "endpoints": [],
        },
        "container": {
            "title": "Cloud Container (PaaS)",
            "base_path": "(Kubernetes API)",
            "docs": "https://docs.arvancloud.ir/en/cloud-container/",
            "summary": "Kubernetes-compatible PaaS. Managed with kubectl/oc against "
            "your namespace token rather than the napi REST API, so it is outside "
            "this server's typed tools.",
            "endpoints": [],
        },
    },
}


def summary() -> dict[str, Any]:
    """A compact overview suitable for returning to a model."""

    services = {
        key: {
            "title": svc["title"],
            "base_path": svc["base_path"],
            "summary": svc["summary"],
            "endpoint_count": len(svc.get("endpoints", [])),
        }
        for key, svc in CATALOG["services"].items()
    }
    return {
        "base_url": CATALOG["base_url"],
        "auth": CATALOG["auth"],
        "regions": CATALOG["regions"],
        "services": services,
        "hint": "Call arvan_capabilities(service='<name>') for the full endpoint "
        "list of a service, then use arvan_request to call any endpoint.",
    }
