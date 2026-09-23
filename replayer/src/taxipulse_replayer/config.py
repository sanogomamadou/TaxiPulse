"""Runtime configuration for the replayer, loaded from environment variables
(see .env.example at the repo root)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class ReplayerConfig:
    project_id: str
    topic: str
    speedup_factor: float
    inject_late_ratio: float
    inject_duplicate_ratio: float
    emulator_host: str | None

    @classmethod
    def from_env(cls) -> ReplayerConfig:
        return cls(
            project_id=os.environ.get("GCP_PROJECT_ID", "taxipulse-mds"),
            topic=os.environ.get("PUBSUB_TOPIC_TRIPS", "taxi-trips"),
            speedup_factor=float(os.environ.get("REPLAYER_SPEEDUP_FACTOR", "60")),
            inject_late_ratio=float(os.environ.get("REPLAYER_INJECT_LATE_RATIO", "0.0")),
            inject_duplicate_ratio=float(os.environ.get("REPLAYER_INJECT_DUPLICATE_RATIO", "0.0")),
            emulator_host=os.environ.get("PUBSUB_EMULATOR_HOST") or None,
        )
