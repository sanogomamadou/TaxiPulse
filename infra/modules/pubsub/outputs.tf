output "topic_id" {
  value = google_pubsub_topic.trips.id
}

output "topic_name" {
  value = google_pubsub_topic.trips.name
}

output "dlq_topic_name" {
  value = google_pubsub_topic.dlq.name
}

output "subscription_id" {
  value = google_pubsub_subscription.trips.id
}

output "subscription_name" {
  value = google_pubsub_subscription.trips.name
}
