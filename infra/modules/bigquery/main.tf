# Raw layer: written directly by the streaming pipeline (STREAMING_INSERTS).
# staging/marts datasets are added in Phase 3 once the SQL transformations
# and BigQuery ML model exist.
resource "google_bigquery_dataset" "raw" {
  project    = var.project_id
  dataset_id = var.raw_dataset_id
  location   = var.region

  description = "Raw layer: data written directly by the streaming pipeline, before any transformation."

  # Portfolio/dev project: let `terraform destroy` fully clean up, including
  # table contents. Would NOT do this for a production warehouse.
  delete_contents_on_destroy = true
}

# Schema kept in sync BY HAND with pipeline/src/taxipulse_pipeline/io/bigquery_io.py's
# ZONE_AGGREGATES_SCHEMA - Terraform owns table creation, the pipeline's own
# CREATE_IF_NEEDED is just a safety net if it's ever run before `terraform apply`.
resource "google_bigquery_table" "zone_aggregates" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "zone_aggregates"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "window_start"
  }

  clustering = ["pickup_location_id"]

  schema = file("${path.module}/schemas/zone_aggregates.json")
}

# Schema kept in sync BY HAND with bigquery_io.py's DEAD_LETTER_SCHEMA.
resource "google_bigquery_table" "dead_letters" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "dead_letters"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "processing_time"
  }

  schema = file("${path.module}/schemas/dead_letters.json")
}
