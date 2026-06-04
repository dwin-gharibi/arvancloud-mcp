locals {
  init_script = <<-EOT
    #!/bin/bash
    set -euxo pipefail
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc || true
    sh -c 'curl -fsSL https://get.docker.com | sh'
    systemctl enable --now docker
    docker run -d --restart always --name arvancloud-mcp \
      -p ${var.mcp_port}:${var.mcp_port} \
      -e ARVAN_API_KEY='${var.api_key}' \
      -e ARVAN_TRANSPORT=streamable-http \
      -e ARVAN_HOST=0.0.0.0 \
      -e ARVAN_PORT=${var.mcp_port} \
      -e ARVAN_STATELESS_HTTP=true \
      -e ARVAN_JSON_RESPONSE=true \
      -e ARVAN_ENABLED_SERVICES='${var.enabled_services}' \
      -e ARVAN_DEFAULT_REGION='${var.region}' \
      -e ARVAN_S3_ACCESS_KEY='${var.s3_access_key}' \
      -e ARVAN_S3_SECRET_KEY='${var.s3_secret_key}' \
      ${var.mcp_image}
  EOT
}

resource "arvan_iaas_security_group" "mcp" {
  region      = var.region
  name        = "${var.server_name}-sg"
  description = "Allow SSH and the MCP HTTP port"
}

resource "arvan_iaas_security_group_rule" "ssh" {
  region            = var.region
  security_group_id = arvan_iaas_security_group.mcp.id
  direction         = "ingress"
  protocol          = "tcp"
  port_from         = "22"
  port_to           = "22"
  ips               = ["0.0.0.0/0"]
  description       = "SSH"
}

resource "arvan_iaas_security_group_rule" "mcp_http" {
  region            = var.region
  security_group_id = arvan_iaas_security_group.mcp.id
  direction         = "ingress"
  protocol          = "tcp"
  port_from         = tostring(var.mcp_port)
  port_to           = tostring(var.mcp_port)
  ips               = ["0.0.0.0/0"]
  description       = "MCP HTTP"
}

resource "arvan_iaas_abrak" "mcp" {
  region    = var.region
  name      = var.server_name
  flavor    = var.flavor
  disk_size = var.disk_size
  networks  = var.networks

  image {
    type = "distributions"
    name = var.image_name
  }

  security_groups = [arvan_iaas_security_group.mcp.name]
  init_script     = local.init_script
}

data "arvan_iaas_abrak" "mcp" {
  depends_on = [arvan_iaas_abrak.mcp]
  region     = var.region
  name       = var.server_name
}
