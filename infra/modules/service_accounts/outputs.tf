output "dataflow_worker_email" {
  value = google_service_account.dataflow_worker.email
}

output "replayer_email" {
  value = google_service_account.replayer.email
}
