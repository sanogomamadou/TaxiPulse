variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "storage_account_name" {
  description = "Globally-unique storage account name (lowercase alphanumeric, 3-24 chars, no hyphens)"
  type        = string
}

variable "containers" {
  description = "ADLS Gen2 filesystem containers to create: Delta Lake raw/staging/marts layers plus a Spark Structured Streaming checkpoint location"
  type        = list(string)
  default     = ["raw", "staging", "marts", "checkpoints"]
}
