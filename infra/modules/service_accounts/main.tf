# --- Dataflow worker: reads Pub/Sub, writes BigQuery, uses the temp bucket ---
# Least privilege: every binding below is scoped to the specific
# topic/subscription/dataset/bucket the pipeline actually touches, never a
# broad project-level Editor/Owner role.
resource "google_service_account" "dataflow_worker" {
  project      = var.project_id
  account_id   = "taxipulse-dataflow-worker"
  display_name = "TaxiPulse Dataflow worker"
  description  = "Identity used by the Dataflow streaming job: reads Pub/Sub, writes BigQuery raw tables, uses the Dataflow temp bucket."
}

# dataflow.worker is inherently project-scoped (no resource-level equivalent)
# and is the minimum role a Dataflow worker VM needs to report status/metrics
# back to the service.
resource "google_project_iam_member" "dataflow_worker_role" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

resource "google_pubsub_subscription_iam_member" "dataflow_worker_subscriber" {
  project      = var.project_id
  subscription = var.pubsub_subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

resource "google_bigquery_dataset_iam_member" "dataflow_worker_data_editor" {
  project    = var.project_id
  dataset_id = var.bigquery_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

resource "google_storage_bucket_iam_member" "dataflow_worker_temp_bucket" {
  bucket = var.dataflow_temp_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

# --- Replayer: only ever needs to publish to the one topic it replays into ---
resource "google_service_account" "replayer" {
  project      = var.project_id
  account_id   = "taxipulse-replayer"
  display_name = "TaxiPulse replayer"
  description  = "Identity used by the replayer script to publish trip events to Pub/Sub."
}

resource "google_pubsub_topic_iam_member" "replayer_publisher" {
  project = var.project_id
  topic   = var.pubsub_topic_name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.replayer.email}"
}
