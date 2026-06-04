output "server" {
  description = "Full details of the provisioned MCP server."
  value       = data.arvan_iaas_abrak.mcp
}

output "mcp_endpoint_hint" {
  description = "Where the MCP will be reachable once cloud-init finishes."
  value       = "http://<server-public-ip>:${var.mcp_port}/mcp (see the 'server' output for the IP)"
}
