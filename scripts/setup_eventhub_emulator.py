"""Verifies the local Event Hubs emulator is reachable and the expected hub
exists, with the partition count declared in infra/local/eventhubs-emulator-config.json.

Unlike the old Pub/Sub emulator, Event Hubs entities aren't created
dynamically via an API call - they're defined statically in the emulator's
Config.json (mounted by docker-compose.yml) and created at container
startup. This script is a connectivity/sanity check, not a provisioning
step.
"""

from __future__ import annotations

import logging
import os
import sys

from azure.eventhub import EventHubProducerClient

logger = logging.getLogger(__name__)

# Well-known connection string for the local emulator (UseDevelopmentEmulator=true
# bypasses real authentication). See infra/local/eventhubs-emulator-config.json
# for the matching namespace/hub definition.
DEFAULT_EMULATOR_CONNECTION_STRING = (
    "Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;"
    "SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;"
)


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger.setLevel(logging.INFO)

    connection_string = os.environ.get(
        "AZURE_EVENTHUB_CONNECTION_STRING", DEFAULT_EMULATOR_CONNECTION_STRING
    )
    eventhub_name = os.environ.get("AZURE_EVENTHUB_NAME", "taxi-trips")

    client = EventHubProducerClient.from_connection_string(
        connection_string, eventhub_name=eventhub_name
    )
    try:
        with client:
            properties = client.get_eventhub_properties()
    except Exception:
        logger.exception(
            "could not reach hub '%s' - is the emulator up? (make emulator-up)", eventhub_name
        )
        return 1

    logger.info(
        "hub '%s' is reachable: %d partition(s)",
        properties["eventhub_name"],
        len(properties["partition_ids"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
