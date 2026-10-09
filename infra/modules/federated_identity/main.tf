# GitHub Actions OIDC - the whole point is that CI authenticates to Azure
# with NO stored secret (no client secret, no JSON key). GitHub's OIDC
# token issuer and this identity's federated credential trust each other
# directly; `azure/login@v2` in the workflow exchanges a short-lived
# GitHub-issued token for an Azure AD token at request time.
resource "azurerm_user_assigned_identity" "github_actions" {
  name                = "${var.name_prefix}-github-actions"
  resource_group_name = var.resource_group_name
  location            = var.location
}

# Scoped to `ref:refs/heads/main` only - deliberately NOT trusting
# pull_request events. A fork's PR workflow run would otherwise be able
# to request a token for this identity, which is a well-known OIDC/
# GitHub Actions supply-chain risk - trust only the branch that actually
# deploys.
resource "azurerm_federated_identity_credential" "main_branch" {
  name                      = "github-main-branch"
  user_assigned_identity_id = azurerm_user_assigned_identity.github_actions.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = "repo:${var.github_repo}:ref:refs/heads/main"
}

# Contributor on the resource group - broad enough for `terraform plan`/
# `apply` to manage any resource this project defines, but scoped to
# just this one resource group, never the subscription.
resource "azurerm_role_assignment" "contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github_actions.principal_id
}

# Contributor alone does not grant the data-plane right to push images -
# that needs its own role, scoped to just this one registry.
resource "azurerm_role_assignment" "acr_push" {
  scope                = var.container_registry_id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github_actions.principal_id
}
