variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCS bucket location"
  type        = string
}

variable "raw_bucket_name" {
  description = "Globally-unique name for the raw TLC data bucket"
  type        = string
}

variable "dataflow_temp_bucket_name" {
  description = "Globally-unique name for the Dataflow staging/temp bucket"
  type        = string
}

variable "raw_data_retention_days" {
  description = "Auto-delete raw data objects after this many days (cost control)"
  type        = number
  default     = 30
}

variable "temp_object_retention_days" {
  description = "Auto-delete Dataflow staging/temp objects after this many days (cost control)"
  type        = number
  default     = 3
}
