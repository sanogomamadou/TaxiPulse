variable "resource_group_name" {
  type = string
}

variable "resource_group_id" {
  type = string
}

variable "location" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "github_repo_owner" {
  type = string
}

variable "github_owner_id" {
  description = "Immutable numeric GitHub user/org ID (gh api repos/OWNER/REPO --jq .owner.id) - GitHub's actual OIDC subject claim includes this appended to the owner login, not just the login alone (found by reading a real AADSTS700213 error from a live CI run, not from the docs)"
  type        = string
}

variable "github_repo_name" {
  type = string
}

variable "github_repo_id" {
  description = "Immutable numeric GitHub repo ID (gh api repos/OWNER/REPO --jq .id)"
  type        = string
}

variable "container_registry_id" {
  type = string
}
