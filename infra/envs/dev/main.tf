module "resource_group" {
  source = "../../modules/resource_group"

  name     = "${var.name_prefix}-rg"
  location = var.location
}

module "event_hubs" {
  source = "../../modules/event_hubs"

  resource_group_name = module.resource_group.name
  location            = var.location
  namespace_name      = "${var.name_prefix}-eventhub-ns"
}

module "storage" {
  source = "../../modules/storage"

  resource_group_name  = module.resource_group.name
  location             = var.location
  storage_account_name = replace("${var.name_prefix}data", "-", "")
}

module "databricks" {
  source = "../../modules/databricks"

  resource_group_name = module.resource_group.name
  location            = var.location
  workspace_name      = "${var.name_prefix}-databricks"
}

module "identities" {
  source = "../../modules/identities"

  resource_group_name   = module.resource_group.name
  location              = var.location
  storage_account_id    = module.storage.storage_account_id
  eventhub_namespace_id = module.event_hubs.namespace_id
  eventhub_name         = module.event_hubs.eventhub_name
}
