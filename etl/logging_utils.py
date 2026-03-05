from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

LOGGER_NAME = "etl"


def configure_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(message)s")


def log_event(stage: str, event: str, **fields: object) -> None:
    payload: dict[str, object] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "event": event,
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    logging.getLogger(LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
