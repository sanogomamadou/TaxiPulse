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
  description = "Basic is the cheapest tier and is sufficient here: this project only ever needs the $Default consumer group (Basic supports it; Standard, which costs more, is only needed for multiple custom consumer groups)."
  type        = string
  default     = "Basic"
}

variable "partition_count" {
  type    = number
  default = 4
}
