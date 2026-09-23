"""Creates the Pub/Sub topics and subscriptions the pipeline expects,
against a running local emulator (see docker-compose.yml / `make emulator-up`).

Idempotent: safely re-run any time the emulator container is restarted
(its state is not persisted between runs).
"""

from __future__ import annotations

import logging
import os

from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


def _project_id() -> str:
    return os.environ.get("GCP_PROJECT_ID", "taxipulse-mds")


def _emulator_host() -> str:
    return os.environ.get("PUBSUB_EMULATOR_HOST", "localhost:8085")


def create_topic(client: pubsub_v1.PublisherClient, project_id: str, topic: str) -> str:
    topic_path = client.topic_path(project_id, topic)
    try:
        client.create_topic(name=topic_path)
        logger.info("created topic %s", topic_path)
    except AlreadyExists:
        logger.info("topic %s already exists", topic_path)
    return topic_path


def create_subscription(
    client: pubsub_v1.SubscriberClient,
    project_id: str,
    subscription: str,
    topic_path: str,
) -> str:
    subscription_path = client.subscription_path(project_id, subscription)
    try:
        client.create_subscription(name=subscription_path, topic=topic_path)
        logger.info("created subscription %s", subscription_path)
    except AlreadyExists:
        logger.info("subscription %s already exists", subscription_path)
    return subscription_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    os.environ["PUBSUB_EMULATOR_HOST"] = _emulator_host()
    project_id = _project_id()

    trips_topic = os.environ.get("PUBSUB_TOPIC_TRIPS", "taxi-trips")
    dlq_topic = os.environ.get("PUBSUB_TOPIC_TRIPS_DLQ", "taxi-trips-dlq")
    trips_subscription = os.environ.get("PUBSUB_SUBSCRIPTION_TRIPS", "taxi-trips-sub")

    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    trips_topic_path = create_topic(publisher, project_id, trips_topic)
    create_topic(publisher, project_id, dlq_topic)
    create_subscription(subscriber, project_id, trips_subscription, trips_topic_path)

    logger.info("emulator setup done for project '%s' at %s", project_id, _emulator_host())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
