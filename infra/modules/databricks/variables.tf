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
  description = "'standard' is deprecated and no longer accepted for new workspaces (confirmed via a 400 DatabricksStandardSkuNotSupported on first apply) - 'premium' is now the effective baseline tier. The workspace itself is still free regardless of tier; only cluster DBU-hours bill, at a higher per-DBU rate than the old Standard tier had."
  type        = string
  default     = "premium"
}
