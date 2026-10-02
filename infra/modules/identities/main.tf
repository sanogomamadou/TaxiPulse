# Least privilege, mirroring the archived GCP version's service_accounts
# module: every role assignment below is scoped to the one specific
# resource (storage account or Event Hub entity) the identity actually
# needs, never a subscription- or resource-group-wide role.
#
# Note: the replayer and pipeline currently authenticate with a Pub/Sub-era
# holdover pattern - a connection string / SAS key - rather than these
# managed identities (azure-identity is already a dependency; wiring
# DefaultAzureCredential through is a natural follow-up, not done here to
# keep this step's scope to the infrastructure itself).

resource "azurerm_user_assigned_identity" "databricks_job" {
  name                = "taxipulse-databricks-job"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "databricks_job_storage" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.databricks_job.principal_id
}

resource "azurerm_role_assignment" "databricks_job_eventhub_receiver" {
  scope                = "${var.eventhub_namespace_id}/eventhubs/${var.eventhub_name}"
  role_definition_name = "Azure Event Hubs Data Receiver"
  principal_id         = azurerm_user_assigned_identity.databricks_job.principal_id
}

resource "azurerm_user_assigned_identity" "replayer" {
  name                = "taxipulse-replayer"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "replayer_eventhub_sender" {
  scope                = "${var.eventhub_namespace_id}/eventhubs/${var.eventhub_name}"
  role_definition_name = "Azure Event Hubs Data Sender"
  principal_id         = azurerm_user_assigned_identity.replayer.principal_id
}
