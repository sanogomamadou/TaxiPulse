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
  description = "ADLS Gen2 filesystem containers to create: Delta Lake raw/staging/marts layers, a Spark Structured Streaming checkpoint location, and a flat 'warehouse' container the API reads from (mirrors the local warehouse_output/ layout - staging/X, marts/Y as blob prefixes under one container - unlike raw/staging/marts above, which are separate top-level containers for the Databricks job's own layering convention)"
  type        = list(string)
  default     = ["raw", "staging", "marts", "checkpoints", "warehouse"]
}
