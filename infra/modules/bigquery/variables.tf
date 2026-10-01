variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "BigQuery dataset location"
  type        = string
}

variable "raw_dataset_id" {
  description = "Dataset ID for the raw layer (written directly by the streaming pipeline)"
  type        = string
  default     = "taxipulse_raw"
}
