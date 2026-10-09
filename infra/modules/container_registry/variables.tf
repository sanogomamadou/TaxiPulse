variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "registry_name" {
  description = "Globally-unique registry name (alphanumeric only, 5-50 chars)"
  type        = string
}
