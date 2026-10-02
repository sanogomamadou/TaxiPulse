variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "workspace_name" {
  type = string
}

variable "sku" {
  description = "'standard' is the cheapest tier and covers everything this project needs (no Unity Catalog / cluster policies requirement)"
  type        = string
  default     = "standard"
}
