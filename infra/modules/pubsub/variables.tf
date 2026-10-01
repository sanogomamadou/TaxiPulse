variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_number" {
  description = "GCP project number, used to address the Pub/Sub service agent for the dead-letter IAM bindings"
  type        = string
}

variable "topic_name" {
  description = "Name of the main trip events topic"
  type        = string
  default     = "taxi-trips"
}

variable "dlq_topic_name" {
  description = "Name of the dead-letter topic"
  type        = string
  default     = "taxi-trips-dlq"
}

variable "subscription_name" {
  description = "Name of the pull subscription the pipeline reads from"
  type        = string
  default     = "taxi-trips-sub"
}

variable "ack_deadline_seconds" {
  description = "How long a subscriber has to ack a message before Pub/Sub redelivers it"
  type        = number
  default     = 30
}

variable "max_delivery_attempts" {
  description = "Number of delivery attempts before a message is sent to the dead-letter topic"
  type        = number
  default     = 5
}

variable "message_retention_duration" {
  description = "How long unacked messages are retained on the main topic"
  type        = string
  default     = "86400s" # 1 day - short on purpose to bound storage cost
}
