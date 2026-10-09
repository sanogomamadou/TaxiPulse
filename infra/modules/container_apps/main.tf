# Consumption-plan Container Apps Environment (no dedicated/reserved
# compute to leave running) requires a Log Analytics workspace - the
# cheapest SKU (PerGB2018, pay-as-you-go) and a short retention, since
# this is a short-lived demo deployment, not a production environment.
resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.app_name}-logs"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "this" {
  name                       = "${var.app_name}-env"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
}

# Least privilege, same pattern as the identities module: this identity
# can pull from the one registry it needs, nothing else - not the admin
# username/password the registry module deliberately disables.
resource "azurerm_user_assigned_identity" "acr_pull" {
  name                = "${var.app_name}-acr-pull"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.container_registry_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.acr_pull.principal_id
}

# Storage auth uses the account key (a Container App secret), not a
# managed identity + RBAC role - same known simplification already made
# for the replayer/pipeline's Event Hubs auth in Phase 2 (see the
# identities module's comment). delta-rs's Azure backend picks up
# AZURE_STORAGE_ACCOUNT_NAME/AZURE_STORAGE_ACCOUNT_KEY from the
# environment automatically - no storage_options wiring needed in the
# API's own code.
resource "azurerm_container_app" "this" {
  name                         = var.app_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.acr_pull.id]
  }

  registry {
    server   = var.container_registry_login_server
    identity = azurerm_user_assigned_identity.acr_pull.id
  }

  secret {
    name  = "storage-account-key"
    value = var.storage_account_key
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "taxipulse-api"
      image  = var.container_image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "TAXIPULSE_WAREHOUSE_OUTPUT"
        value = var.warehouse_output_path
      }
      env {
        name  = "TAXIPULSE_PIPELINE_OUTPUT"
        value = var.pipeline_output_path
      }
      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = var.storage_account_name
      }
      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "storage-account-key"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
