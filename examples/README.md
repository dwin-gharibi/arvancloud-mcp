# Examples

Recipes for common workflows. In an MCP client (Claude, Cursor, Gemini, …) you
just ask in natural language — these show the tools the model strings together.

## Inspect the server (offline, no API key)

```bash
python examples/inspect_server.py
```
Lists how many tools are exposed, runs `arvan_doctor`, and prints the service
catalogue — a quick check that the server is wired up.

## Provision a web server and install nginx

> "Spin up a small Ubuntu server in ir-thr-c2 and install nginx."

1. `arvan_list_plans`, `arvan_list_images` — pick a flavor + Ubuntu image.
2. `arvan_provision_server(name="web1", flavor_id=..., image_id=..., packages=["nginx"])`
   — generates an SSH key, creates the server, waits for boot, installs over SSH.
3. `arvan_net_http_check(url="http://<ip>")` — confirm it serves traffic.

## Host a static website on Object Storage

> "Deploy ./site to a public bucket and give me the URL."

1. `arvan_s3_create_bucket(bucket="my-site", acl="public-read")`
2. `arvan_s3_sync_local_dir(bucket="my-site", local_dir="./site", acl="public-read")`
3. `arvan_s3_enable_static_website(bucket="my-site")` → returns the website endpoint.

## Audit security

> "Audit my security groups and grade my site's headers."

1. `arvan_security_audit_security_groups(region="ir-thr-c2")`
2. `arvan_security_http_headers(url="https://example.com")`
3. `arvan_net_tls_cert(host="example.com")` — check expiry.

## Validate & apply Terraform

> "Validate this Terraform, show the plan, and apply if clean."

1. `arvan_iac_terraform_validate(files={...})`
2. `arvan_iac_terraform_plan(files={...})`
3. `arvan_iac_terraform_apply(files={...}, auto_approve=true)`

## Deploy to Kubernetes / ArvanCloud PaaS

1. `arvan_iac_validate_kubernetes(manifest=...)`
2. `arvan_k8s_apply(directory="deploy/kubernetes", kubeconfig=...)`
3. `arvan_k8s_get(resource="pods", namespace="arvancloud-mcp", kubeconfig=...)`

## Schedule a recurring scan with a Slack ping

> "Every hour, scan example.com headers and Slack me the result."

```text
arvan_task_submit(
  tool="arvan_security_http_headers",
  arguments={"url": "https://example.com"},
  interval_seconds=3600,
  announce_webhook="https://hooks.slack.com/services/...")
```
