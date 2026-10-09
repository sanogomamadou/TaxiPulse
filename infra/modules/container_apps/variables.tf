variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "app_name" {
  type = string
}

variable "container_registry_id" {
  type = string
}

variable "container_registry_login_server" {
  type = string
}

variable "container_image" {
  description = "Full image reference, e.g. <registry>.azurecr.io/taxipulse-api:latest"
  type        = string
}

variable "warehouse_output_path" {
  description = "abfss:// base path the API reads warehouse marts from"
  type        = string
}

variable "pipeline_output_path" {
  description = "abfss:// base path the API reads the streaming pipeline's zone_aggregates from"
  type        = string
}

variable "storage_account_name" {
  type = string
}

variable "storage_account_key" {
  type      = string
  sensitive = true
}
