# Namespace capacity=1 (1 throughput unit) is the minimum billable amount -
# an Event Hubs namespace bills per provisioned throughput unit-hour even
# when idle, so this is also the cheapest viable configuration. Destroy
# between sessions (`make destroy`) rather than leaving it provisioned.
resource "azurerm_eventhub_namespace" "this" {
  name                = var.namespace_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  capacity            = 1
}

resource "azurerm_eventhub" "trips" {
  name              = var.eventhub_name
  namespace_id      = azurerm_eventhub_namespace.this.id
  partition_count   = var.partition_count
  message_retention = 1 # day - plenty for a demo/replay workload (Standard tier allows up to 7)
}
