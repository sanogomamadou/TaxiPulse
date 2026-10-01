output "raw_bucket_name" {
  value = google_storage_bucket.raw_data.name
}

output "dataflow_temp_bucket_name" {
  value = google_storage_bucket.dataflow_temp.name
}

output "dataflow_temp_bucket_url" {
  value = google_storage_bucket.dataflow_temp.url
}
