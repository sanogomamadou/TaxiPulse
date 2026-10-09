output "storage_account_name" {
  value = azurerm_storage_account.this.name
}

output "storage_account_id" {
  value = azurerm_storage_account.this.id
}

output "primary_dfs_endpoint" {
  description = "abfss:// base endpoint for Delta Lake paths"
  value       = azurerm_storage_account.this.primary_dfs_endpoint
}

output "primary_access_key" {
  description = "Storage account key - used for the API's delta-rs Azure auth (AZURE_STORAGE_ACCOUNT_KEY) and for uploading local data. A known simplification vs. managed-identity + RBAC, same as the replayer/pipeline's Event Hubs connection-string auth (see the identities module)."
  value       = azurerm_storage_account.this.primary_access_key
  sensitive   = true
}
