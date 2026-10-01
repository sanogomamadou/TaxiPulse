# Main topic the replayer publishes to, and the pipeline reads from.
resource "google_pubsub_topic" "trips" {
  project = var.project_id
  name    = var.topic_name

  message_retention_duration = var.message_retention_duration
}

# Dead-letter topic: Pub/Sub itself forwards a message here after
# max_delivery_attempts failed deliveries to the main subscription. This is
# separate from (and complementary to) the pipeline's own application-level
# dead-lettering of malformed message *payloads* (transforms/parsing.py) -
# this one catches messages the subscriber can't even process/ack at all.
resource "google_pubsub_topic" "dlq" {
  project = var.project_id
  name    = var.dlq_topic_name
}

resource "google_pubsub_subscription" "trips" {
  project = var.project_id
  name    = var.subscription_name
  topic   = google_pubsub_topic.trips.id

  ack_deadline_seconds = var.ack_deadline_seconds

  # Never expire from inactivity - a demo/portfolio subscription may sit
  # idle between sessions and should still be there next time.
  expiration_policy {
    ttl = ""
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = var.max_delivery_attempts
  }
}

# The dead-letter policy above only works if Pub/Sub's own service agent is
# allowed to publish to the DLQ topic and to ack/nack on the source
# subscription - these bindings are required, not optional.
resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "dlq_subscriber" {
  project      = var.project_id
  subscription = google_pubsub_subscription.trips.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
