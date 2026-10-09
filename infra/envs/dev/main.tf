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

module "container_registry" {
  source = "../../modules/container_registry"

  resource_group_name = module.resource_group.name
  location            = var.location
  registry_name       = replace("${var.name_prefix}acr", "-", "")
}

module "federated_identity" {
  source = "../../modules/federated_identity"

  resource_group_name   = module.resource_group.name
  resource_group_id     = module.resource_group.id
  location              = var.location
  name_prefix           = var.name_prefix
  github_repo_owner     = var.github_repo_owner
  github_owner_id       = var.github_owner_id
  github_repo_name      = var.github_repo_name
  github_repo_id        = var.github_repo_id
  container_registry_id = module.container_registry.id
}

module "container_apps" {
  source = "../../modules/container_apps"

  resource_group_name             = module.resource_group.name
  location                        = var.location
  app_name                        = "${var.name_prefix}-api"
  container_registry_id           = module.container_registry.id
  container_registry_login_server = module.container_registry.login_server
  container_image                 = "${module.container_registry.login_server}/taxipulse-api:${var.api_image_tag}"
  warehouse_output_path           = "abfss://warehouse@${module.storage.storage_account_name}.dfs.core.windows.net"
  pipeline_output_path            = "abfss://raw@${module.storage.storage_account_name}.dfs.core.windows.net"
  storage_account_name            = module.storage.storage_account_name
  storage_account_key             = module.storage.primary_access_key
}
