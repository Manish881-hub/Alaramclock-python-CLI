"""Tests for alarm_clock.storage."""

from alarm_clock.config import Config, StorageConfig
from alarm_clock.models import Alarm
from alarm_clock.storage import load_alarms, save_alarms


def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="t-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


class TestLoadAlarms:
    def test_no_store_returns_empty(self):
        cfg = Config(storage=StorageConfig(path="/nonexistent/path/alarms.json"))
        assert load_alarms(cfg) == []

    def test_load_empty_json(self, tmp_path):
        store = tmp_path / "alarms.json"
        store.write_text("[]")
        cfg = Config(storage=StorageConfig(path=str(store)))
        assert load_alarms(cfg) == []

    def test_corrupt_store_returns_empty(self, tmp_path):
        store = tmp_path / "alarms.json"
        store.write_text("not valid json {{{")
        cfg = Config(storage=StorageConfig(path=str(store)))
        assert load_alarms(cfg) == []


class TestSaveAlarms:
    def test_save_empty_list(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        save_alarms(cfg, [])
        assert store.exists()
        assert store.read_text() == "[]"

    def test_save_and_load_round_trip(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        alarms = [
            make_alarm(id="a1", label="Wake up", hour=7, minute=0, repeat_daily=True),
            make_alarm(id="a2", label="Meeting", hour=9, minute=30),
        ]
        save_alarms(cfg, alarms)
        loaded = load_alarms(cfg)

        assert len(loaded) == 2
        assert loaded[0].label == "Wake up"
        assert loaded[0].repeat_daily is True
        assert loaded[0].hour == 7
        assert loaded[0].minute == 0
        assert loaded[1].label == "Meeting"
        assert loaded[1].hour == 9
        assert loaded[1].minute == 30

    def test_preserves_snoozed_until(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        snooze = "2026-06-16T12:00:00"
        alarms = [make_alarm(id="x", snoozed_until=snooze)]
        save_alarms(cfg, alarms)
        loaded = load_alarms(cfg)
        assert loaded[0].snoozed_until == snooze

    def test_preserves_inactive_state(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        alarms = [make_alarm(id="y", active=False)]
        save_alarms(cfg, alarms)
        loaded = load_alarms(cfg)
        assert loaded[0].active is False

    def test_multiple_saves(self, tmp_path):
        store = tmp_path / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(store)))
        alarms = [make_alarm(id="a")]
        save_alarms(cfg, alarms)
        alarms.append(make_alarm(id="b"))
        save_alarms(cfg, alarms)
        loaded = load_alarms(cfg)
        assert len(loaded) == 2

    def test_storage_path_is_created(self, tmp_path):
        nested = tmp_path / "deeply" / "nested" / "alarms.json"
        cfg = Config(storage=StorageConfig(path=str(nested)))
        save_alarms(cfg, [make_alarm()])
        assert nested.exists()
