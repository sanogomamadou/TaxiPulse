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
