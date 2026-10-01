"""Runtime configuration for the replayer, loaded from environment variables
(see .env.example at the repo root)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class ReplayerConfig:
    eventhub_connection_string: str
    eventhub_name: str
    speedup_factor: float
    inject_late_ratio: float
    inject_duplicate_ratio: float

    @classmethod
    def from_env(cls) -> ReplayerConfig:
        return cls(
            eventhub_connection_string=os.environ.get("AZURE_EVENTHUB_CONNECTION_STRING", ""),
            eventhub_name=os.environ.get("AZURE_EVENTHUB_NAME", "taxi-trips"),
            speedup_factor=float(os.environ.get("REPLAYER_SPEEDUP_FACTOR", "60")),
            inject_late_ratio=float(os.environ.get("REPLAYER_INJECT_LATE_RATIO", "0.0")),
            inject_duplicate_ratio=float(os.environ.get("REPLAYER_INJECT_DUPLICATE_RATIO", "0.0")),
        )
