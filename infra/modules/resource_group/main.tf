# Single resource group holding every TaxiPulse resource, so a single
# `terraform destroy` (or even just deleting the resource group) cleans up
# everything - important given the $100 student credit budget.
resource "azurerm_resource_group" "this" {
  name     = var.name
  location = var.location
}
