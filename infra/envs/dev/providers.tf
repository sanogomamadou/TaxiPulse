terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Local state on purpose for this solo portfolio project - same documented
  # tradeoff as the archived GCP version. terraform.tfstate is gitignored.
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id

  # Default behavior (and "core") both try to list/populate a Resource
  # Provider registration cache before doing anything else, and that list
  # call itself failed repeatedly against this subscription ("unexpected
  # end of JSON input" - an Azure API flakiness, not a config issue). Every
  # provider this config needs (Microsoft.EventHub, Storage, Databricks,
  # ManagedIdentity, Authorization, Resources) is already registered on this
  # subscription (confirmed via `az provider show`), so "none" - skip
  # registration handling entirely - sidesteps the failing call safely.
  resource_provider_registrations = "none"
}
