variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "namespace_name" {
  description = "Globally-unique Event Hubs namespace name"
  type        = string
}

variable "eventhub_name" {
  type    = string
  default = "taxi-trips"
}

variable "sku" {
  description = "Must be Standard or higher: the Kafka-compatible protocol (which the pipeline's spark-sql-kafka-0-10 reader depends on) is only available on Standard/Premium/Dedicated - Basic rejects it outright with a SaslAuthenticationException, confirmed against the real service (Basic was the original, cheaper choice, picked before anyone had tried an actual Kafka connection against it)."
  type        = string
  default     = "Standard"
}

variable "partition_count" {
  type    = number
  default = 4
}
