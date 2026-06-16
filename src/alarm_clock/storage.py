"""Alarm persistence with atomic JSON writes."""

import contextlib
import json
import threading

from alarm_clock.config import Config
from alarm_clock.logging_conf import get_logger
from alarm_clock.models import Alarm

logger = get_logger(__name__)

_lock = threading.Lock()


def load_alarms(config: Config) -> list[Alarm]:
    """Load alarms from JSON file."""
    store_path = config.get_storage_path()
    if not store_path.exists():
        logger.debug("No alarm store found at {}", store_path)
        return []

    try:
        with store_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        alarms = [Alarm.from_dict(item) for item in data]
        logger.info("Loaded {} alarms from {}", len(alarms), store_path)
        return alarms
    except Exception as e:
        logger.error("Failed to load alarms from {}: {}", store_path, e)
        logger.warning("Starting with empty alarm list")
        return []


def save_alarms(config: Config, alarms: list[Alarm]) -> None:
    """Save alarms to JSON file atomically."""
    store_path = config.get_storage_path()
    store_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = store_path.with_suffix(".tmp")

    try:
        with _lock:
            data = [alarm.to_dict() for alarm in alarms]
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(store_path)
        logger.debug("Saved {} alarms to {}", len(alarms), store_path)
    except Exception as e:
        logger.error("Failed to save alarms to {}: {}", store_path, e)
        if tmp_path.exists():
            with contextlib.suppress(Exception):
                tmp_path.unlink()
        raise
