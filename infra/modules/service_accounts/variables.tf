variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "pubsub_topic_name" {
  description = "Main trip events topic name (replayer publishes here)"
  type        = string
}

variable "pubsub_subscription_name" {
  description = "Subscription name the Dataflow worker reads from"
  type        = string
}

variable "bigquery_dataset_id" {
  description = "Raw dataset ID the Dataflow worker writes to"
  type        = string
}

variable "dataflow_temp_bucket_name" {
  description = "Dataflow staging/temp bucket name"
  type        = string
}
