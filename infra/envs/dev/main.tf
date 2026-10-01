data "google_project" "this" {
  project_id = var.project_id
}

module "pubsub" {
  source = "../../modules/pubsub"

  project_id     = var.project_id
  project_number = data.google_project.this.number

  depends_on = [google_project_service.required]
}

module "gcs" {
  source = "../../modules/gcs"

  project_id                = var.project_id
  region                    = var.region
  raw_bucket_name           = "${var.project_id}-raw-data"
  dataflow_temp_bucket_name = "${var.project_id}-dataflow-temp"

  depends_on = [google_project_service.required]
}

module "bigquery" {
  source = "../../modules/bigquery"

  project_id = var.project_id
  region     = var.region

  depends_on = [google_project_service.required]
}

module "service_accounts" {
  source = "../../modules/service_accounts"

  project_id                = var.project_id
  pubsub_topic_name         = module.pubsub.topic_name
  pubsub_subscription_name  = module.pubsub.subscription_name
  bigquery_dataset_id       = module.bigquery.raw_dataset_id
  dataflow_temp_bucket_name = module.gcs.dataflow_temp_bucket_name
}
