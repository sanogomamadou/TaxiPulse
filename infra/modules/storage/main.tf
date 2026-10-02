# LRS (locally-redundant) is the cheapest replication tier - fine for a
# dev/demo project, would NOT be the right choice for production data.
resource "azurerm_storage_account" "this" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Hierarchical namespace = ADLS Gen2, required for Delta Lake / Databricks
  # best practice (vs. plain Blob storage).
  is_hns_enabled = true
}

resource "azurerm_storage_container" "containers" {
  for_each              = toset(var.containers)
  name                  = each.value
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}
