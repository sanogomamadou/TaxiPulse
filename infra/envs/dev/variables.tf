variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Primary Azure region for all resources"
  type        = string
  default     = "westeurope"
}

variable "name_prefix" {
  description = "Prefix used for resource names - keep it short, lowercase, hyphen-free-safe (the storage account name derives from this with hyphens stripped, and must be globally unique)"
  type        = string
  default     = "taxipulse-mds"
}
