variable "resource_group_name" {
  type = string
}

variable "resource_group_id" {
  type = string
}

variable "location" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "github_repo" {
  description = "GitHub repo in owner/name form, e.g. sanogomamadou/TaxiPulse"
  type        = string
}

variable "container_registry_id" {
  type = string
}
