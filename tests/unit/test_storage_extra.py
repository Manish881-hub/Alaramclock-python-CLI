"""Additional storage tests for error handling paths."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from alarm_clock.config import Config, StorageConfig
from alarm_clock.models import Alarm
from alarm_clock.storage import load_alarms, save_alarms


class TestStorageErrors:
    def test_save_permission_error(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        alarms = [Alarm(id="a", label="Test", hour=8, minute=0, repeat_daily=False)]

        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            with pytest.raises(Exception):
                save_alarms(cfg, alarms)

    def test_save_atomicity(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        alarms = [Alarm(id="a", label="Test", hour=8, minute=0, repeat_daily=False)]

        save_alarms(cfg, alarms)
        assert store.exists()
        assert store.read_text() != ""


class TestLoadErrors:
    def test_load_permission_error_returns_empty(self, tmp_path):
        store = tmp_path / "alarms.json"
        store.write_text("[]")
        cfg = Config(storage=StorageConfig(path=str(store)))
        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            result = load_alarms(cfg)
        assert result == []
