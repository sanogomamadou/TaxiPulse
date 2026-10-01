locals {
  required_apis = [
    "pubsub.googleapis.com",
    "bigquery.googleapis.com",
    "dataflow.googleapis.com",
    "storage.googleapis.com",
    "compute.googleapis.com", # Dataflow workers run on Compute Engine VMs
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  # Never disable an API (or its dependents) as a side effect of
  # `terraform destroy` - other things in the project may rely on it being
  # enabled, and re-enabling is a manual step we'd rather force deliberately.
  disable_dependent_services = false
  disable_on_destroy         = false
}
