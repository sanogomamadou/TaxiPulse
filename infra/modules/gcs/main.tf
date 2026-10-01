# Holds raw TLC Parquet samples/batch loads that need to live in GCS rather
# than just locally (e.g. for a Composer/BigQuery batch load in Phase 3).
resource "google_storage_bucket" "raw_data" {
  project                     = var.project_id
  name                        = var.raw_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true

  # Portfolio/dev project: let `terraform destroy` empty the bucket instead
  # of failing on non-empty buckets. Would NOT do this for production data.
  force_destroy = true

  lifecycle_rule {
    condition {
      age = var.raw_data_retention_days
    }
    action {
      type = "Delete"
    }
  }
}

# Dataflow's required staging/temp location for pipeline artifacts and
# intermediate shuffle data.
resource "google_storage_bucket" "dataflow_temp" {
  project                     = var.project_id
  name                        = var.dataflow_temp_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = var.temp_object_retention_days
    }
    action {
      type = "Delete"
    }
  }
}
