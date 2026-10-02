output "namespace_name" {
  value = azurerm_eventhub_namespace.this.name
}

output "namespace_id" {
  value = azurerm_eventhub_namespace.this.id
}

output "eventhub_name" {
  value = azurerm_eventhub.trips.name
}

output "kafka_bootstrap_servers" {
  description = "Event Hubs' Kafka-compatible endpoint, for spark-sql-kafka-0-10"
  value       = "${azurerm_eventhub_namespace.this.name}.servicebus.windows.net:9093"
}
