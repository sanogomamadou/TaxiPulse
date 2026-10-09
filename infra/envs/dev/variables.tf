variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Primary Azure region for all resources. Must be one this subscription's 'Allowed resource deployment regions' policy permits - check with `az policy assignment list` before changing (Azure for Students subscriptions are commonly restricted to a handful of regions, e.g. francecentral, germanywestcentral, swedencentral, switzerlandnorth, polandcentral - NOT westeurope, discovered the hard way via a 403 RequestDisallowedByAzure)."
  type        = string
  default     = "francecentral"
}

variable "name_prefix" {
  description = "Prefix used for resource names - keep it short, lowercase, hyphen-free-safe (the storage account name derives from this with hyphens stripped, and must be globally unique)"
  type        = string
  default     = "taxipulse-mds"
}

variable "api_image_tag" {
  description = "Tag of the taxipulse-api image already pushed to the container registry (push it before applying the container_apps module - Terraform doesn't build/push images itself)"
  type        = string
  default     = "latest"
}
