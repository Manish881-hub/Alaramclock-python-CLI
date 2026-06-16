"""Integration tests for alarm_clock end-to-end workflows."""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from alarm_clock.config import Config, StorageConfig
from alarm_clock.models import Alarm
from alarm_clock.storage import load_alarms, save_alarms
from alarm_clock.scheduler import AlarmMonitor
from alarm_clock.service import get_executable_path


@pytest.fixture
def config(tmp_path):
    return Config(storage=StorageConfig(path=str(tmp_path / "alarms.json")))


@pytest.fixture
def lock():
    return threading.Lock()


class TestAlarmLifecycle:
    """Full lifecycle: create, persist, load, modify, delete."""

    def test_create_persist_load(self, config):
        alarms = [
            Alarm(id="a1", label="Morning", hour=7, minute=30, repeat_daily=True),
            Alarm(id="a2", label="Meeting", hour=10, minute=0, repeat_daily=False),
        ]
        save_alarms(config, alarms)
        loaded = load_alarms(config)
        assert len(loaded) == 2
        assert loaded[0].label == "Morning"
        assert loaded[0].repeat_daily is True
        assert loaded[1].label == "Meeting"
        assert loaded[1].repeat_daily is False

    def test_snooze_persists(self, config):
        alarms = [Alarm(id="s1", label="Snooze Test", hour=8, minute=0, repeat_daily=True)]
        save_alarms(config, alarms)
        snooze_until = (datetime.now() + timedelta(minutes=5)).isoformat()
        alarms[0].snoozed_until = snooze_until
        save_alarms(config, alarms)
        loaded = load_alarms(config)
        assert loaded[0].snoozed_until == snooze_until

    def test_delete_and_verify(self, config):
        alarms = [
            Alarm(id="k1", label="Keep", hour=7, minute=0, repeat_daily=True),
            Alarm(id="k2", label="Remove", hour=8, minute=0, repeat_daily=False),
        ]
        save_alarms(config, alarms)
        alarms.pop(1)
        save_alarms(config, alarms)
        loaded = load_alarms(config)
        assert len(loaded) == 1
        assert loaded[0].label == "Keep"

    def test_disable_and_reactivate(self, config):
        alarms = [Alarm(id="t1", label="Toggle", hour=9, minute=0, repeat_daily=True)]
        save_alarms(config, alarms)
        alarms[0].active = False
        save_alarms(config, alarms)
        loaded = load_alarms(config)
        assert loaded[0].active is False
        alarms[0].active = True
        save_alarms(config, alarms)
        loaded = load_alarms(config)
        assert loaded[0].active is True


class TestMonitorThreading:
    """Test AlarmMonitor threading behavior."""

    def test_monitor_starts_and_stops(self, config, lock):
        callback = lambda a: None
        monitor = AlarmMonitor(config, [], lock, callback)
        monitor.start()
        assert monitor.is_alive()
        monitor.stop()
        monitor.join(timeout=3)
        assert not monitor.is_alive()

    def test_snooze_updates_state(self, config, lock):
        alarms = [Alarm(id="sn1", label="Snoozable", hour=12, minute=0, repeat_daily=True)]
        monitor = AlarmMonitor(config, alarms, lock, lambda a: None)
        assert alarms[0].snoozed_until is None
        monitor.snooze_alarm(alarms[0])
        assert alarms[0].snoozed_until is not None

    def test_dismiss_disables_one_shot(self, config, lock):
        alarms = [Alarm(id="ds1", label="Dismiss Me", hour=12, minute=0, repeat_daily=False)]
        monitor = AlarmMonitor(config, alarms, lock, lambda a: None)
        monitor.dismiss_alarm(alarms[0])
        assert alarms[0].active is False
        assert alarms[0].snoozed_until is None


class TestExecutablePath:
    def test_get_executable_path_normal(self):
        path = get_executable_path()
        assert "python" in path or "python3" in path


class TestDataIntegrity:
    """Ensure no data corruption on round-trips."""

    def test_json_integrity(self, config):
        alarms = [
            Alarm(id="i1", label="Alpha", hour=1, minute=1, repeat_daily=False, active=True),
            Alarm(id="i2", label="Beta", hour=2, minute=2, repeat_daily=True, active=False,
                  snoozed_until="2026-06-16T12:00:00"),
        ]
        save_alarms(config, alarms)
        store_path = config.get_storage_path()
        raw = json.loads(store_path.read_text())
        assert len(raw) == 2
        assert raw[0]["id"] == "i1"
        assert raw[0]["label"] == "Alpha"
        assert raw[0]["hour"] == 1
        assert raw[0]["minute"] == 1
        assert raw[0]["repeat_daily"] is False
        assert raw[0]["active"] is True
        assert raw[1]["id"] == "i2"
        assert raw[1]["repeat_daily"] is True
        assert raw[1]["active"] is False
        assert raw[1]["snoozed_until"] == "2026-06-16T12:00:00"

    def test_concurrent_save(self, config):
        alarms = [Alarm(id="c1", label="Concurrent", hour=3, minute=0, repeat_daily=False)]
        errors = []

        def save_thread():
            try:
                for _ in range(10):
                    save_alarms(config, alarms)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        loaded = load_alarms(config)
        assert len(loaded) == 1
