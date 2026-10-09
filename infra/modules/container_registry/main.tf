# Basic SKU - cheapest tier, sufficient for one image pulled by one
# Container App. Admin credentials disabled (admin_enabled = false) -
# the Container App pulls via its own managed identity + an AcrPull role
# assignment (see the container_apps module), not a shared admin
# username/password.
resource "azurerm_container_registry" "this" {
  name                = var.registry_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
}
