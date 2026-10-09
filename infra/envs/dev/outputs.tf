output "resource_group_name" {
  value = module.resource_group.name
}

output "eventhub_namespace_name" {
  value = module.event_hubs.namespace_name
}

output "eventhub_kafka_bootstrap_servers" {
  value = module.event_hubs.kafka_bootstrap_servers
}

output "storage_account_name" {
  value = module.storage.storage_account_name
}

output "databricks_workspace_url" {
  value = module.databricks.workspace_url
}

output "databricks_job_identity_client_id" {
  value = module.identities.databricks_job_identity_client_id
}

output "replayer_identity_client_id" {
  value = module.identities.replayer_identity_client_id
}

output "container_registry_login_server" {
  value = module.container_registry.login_server
}

output "api_fqdn" {
  value = module.container_apps.fqdn
}

output "github_actions_client_id" {
  description = "AZURE_CLIENT_ID for the GitHub Actions OIDC login step"
  value       = module.federated_identity.client_id
}

output "github_actions_tenant_id" {
  description = "AZURE_TENANT_ID for the GitHub Actions OIDC login step"
  value       = module.federated_identity.tenant_id
}
