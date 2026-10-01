output "pubsub_topic_name" {
  value = module.pubsub.topic_name
}

output "pubsub_subscription_name" {
  value = module.pubsub.subscription_name
}

output "raw_bucket_name" {
  value = module.gcs.raw_bucket_name
}

output "dataflow_temp_bucket_name" {
  value = module.gcs.dataflow_temp_bucket_name
}

output "bigquery_raw_dataset_id" {
  value = module.bigquery.raw_dataset_id
}

output "zone_aggregates_table_id" {
  value = module.bigquery.zone_aggregates_table_id
}

output "dataflow_worker_service_account" {
  value = module.service_accounts.dataflow_worker_email
}

output "replayer_service_account" {
  value = module.service_accounts.replayer_email
}
