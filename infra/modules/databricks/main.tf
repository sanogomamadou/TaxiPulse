# The workspace resource itself is free to provision and leave running -
# Databricks only bills for compute (DBUs) while a cluster/SQL warehouse is
# actually running. Unlike Event Hubs/Storage, there's no strong cost reason
# to destroy this between sessions - just make sure no cluster is left
# running, and prefer clusters with a short auto-termination timeout.
resource "azurerm_databricks_workspace" "this" {
  name                = var.workspace_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
}
