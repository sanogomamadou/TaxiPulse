terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Local state on purpose for this solo portfolio project - no remote
  # backend bootstrapping chicken-and-egg (the GCS bucket that would hold
  # the state doesn't exist until the first apply). A team project would use
  # a GCS backend instead. terraform.tfstate is gitignored.
}

provider "google" {
  project = var.project_id
  region  = var.region
}
