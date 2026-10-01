output "raw_dataset_id" {
  value = google_bigquery_dataset.raw.dataset_id
}

output "zone_aggregates_table_id" {
  value = "${var.project_id}:${google_bigquery_dataset.raw.dataset_id}.${google_bigquery_table.zone_aggregates.table_id}"
}

output "dead_letters_table_id" {
  value = "${var.project_id}:${google_bigquery_dataset.raw.dataset_id}.${google_bigquery_table.dead_letters.table_id}"
}
