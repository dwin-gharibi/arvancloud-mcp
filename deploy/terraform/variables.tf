variable "api_key" {
  description = "ArvanCloud machine-user access key, e.g. 'Apikey xxxxx'. Used by Terraform AND injected into the MCP server."
  type        = string
  sensitive   = true
}

variable "region" {
  description = "ArvanCloud region code."
  type        = string
  default     = "ir-thr-c2"
}

variable "server_name" {
  description = "Name of the cloud server that will run the MCP."
  type        = string
  default     = "arvancloud-mcp"
}

variable "flavor" {
  description = "Plan/flavor id (see `arvan_list_plans` or the panel)."
  type        = string
  default     = "g1-1-1-0"
}

variable "image_name" {
  description = "OS image name."
  type        = string
  default     = "ubuntu/22.04"
}

variable "disk_size" {
  description = "Root disk size in GB."
  type        = number
  default     = 25
}

variable "networks" {
  description = "Networks to attach (must include a public network for inbound access)."
  type        = list(string)
  default     = ["public207"]
}

variable "mcp_image" {
  description = "Container image of the MCP server (push the repo's Dockerfile to a registry)."
  type        = string
  default     = "ghcr.io/dwin-gharibi/arvancloud-mcp:latest"
}

variable "mcp_port" {
  description = "Port the MCP server listens on."
  type        = number
  default     = 8000
}

variable "enabled_services" {
  description = "ARVAN_ENABLED_SERVICES for the MCP."
  type        = string
  default     = "all"
}

variable "s3_access_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "s3_secret_key" {
  type      = string
  default   = ""
  sensitive = true
}
