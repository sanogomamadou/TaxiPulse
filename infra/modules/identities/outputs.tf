output "databricks_job_identity_client_id" {
  value = azurerm_user_assigned_identity.databricks_job.client_id
}

output "replayer_identity_client_id" {
  value = azurerm_user_assigned_identity.replayer.client_id
}
