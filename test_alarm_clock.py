"""
test_alarm_clock.py — Unit tests for alarm_clock.py

Run with:  python -m pytest test_alarm_clock.py -v
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from alarm_clock import Alarm, AlarmMonitor, parse_time, load_alarms, save_alarms


# ─── parse_time ───────────────────────────────────────────────────────────────

class TestParseTime:
    def test_valid_times(self):
        assert parse_time("07:30") == (7, 30)
        assert parse_time("00:00") == (0, 0)
        assert parse_time("23:59") == (23, 59)
        assert parse_time(" 9:05 ") == (9, 5)  # tolerates whitespace

    def test_missing_colon_raises(self):
        with pytest.raises(ValueError):
            parse_time("730")

    def test_too_many_parts_raises(self):
        with pytest.raises(ValueError):
            parse_time("7:30:00")

    def test_hour_out_of_range_raises(self):
        with pytest.raises(ValueError):
            parse_time("24:00")

    def test_minute_out_of_range_raises(self):
        with pytest.raises(ValueError):
            parse_time("07:60")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError):
            parse_time("ab:cd")


# ─── Alarm.next_trigger ───────────────────────────────────────────────────────

def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="test-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


class TestNextTrigger:

    def test_inactive_returns_none(self):
        assert make_alarm(active=False).next_trigger() is None

    def test_future_alarm_fires_today(self):
        future = datetime.now() + timedelta(hours=2)
        a = make_alarm(hour=future.hour, minute=future.minute)
        nxt = a.next_trigger()
        assert nxt is not None
        assert nxt.date() == datetime.now().date()

    def test_past_one_shot_returns_none(self):
        past = datetime.now() - timedelta(hours=2)
        a = make_alarm(hour=past.hour, minute=past.minute, repeat_daily=False)
        assert a.next_trigger() is None

    def test_past_repeating_fires_tomorrow(self):
        past = datetime.now() - timedelta(hours=2)
        a = make_alarm(hour=past.hour, minute=past.minute, repeat_daily=True)
        nxt = a.next_trigger()
        assert nxt is not None
        assert nxt.date() == (datetime.now() + timedelta(days=1)).date()

    def test_active_snooze_returns_snooze_time(self):
        snooze_dt = datetime.now() + timedelta(minutes=5)
        a = make_alarm(snoozed_until=snooze_dt.isoformat())
        nxt = a.next_trigger()
        assert nxt is not None
        # Should be within 1 second of the snooze time
        assert abs((nxt - snooze_dt).total_seconds()) < 1

    def test_expired_snooze_falls_through_to_schedule(self):
        """An expired snooze should be ignored; the normal schedule takes over."""
        past_snooze = (datetime.now() - timedelta(minutes=5)).isoformat()
        future = datetime.now() + timedelta(hours=1)
        a = make_alarm(hour=future.hour, minute=future.minute,
                       snoozed_until=past_snooze)
        nxt = a.next_trigger()
        assert nxt is not None
        assert nxt.date() == datetime.now().date()

    def test_time_str_zero_padded(self):
        a = make_alarm(hour=7, minute=5)
        assert a.time_str == "07:05"


# ─── Persistence ──────────────────────────────────────────────────────────────

class TestPersistence:

    def test_round_trip(self, tmp_path):
        store = tmp_path / "alarms.json"
        alarms = [
            make_alarm(id="a1", label="Wake up", hour=7, minute=0, repeat_daily=True),
            make_alarm(id="a2", label="Meeting", hour=9, minute=30),
        ]
        with patch("alarm_clock.STORE_PATH", store):
            save_alarms(alarms)
            loaded = load_alarms()

        assert len(loaded) == 2
        assert loaded[0].label == "Wake up"
        assert loaded[0].repeat_daily is True
        assert loaded[1].hour == 9
        assert loaded[1].minute == 30

    def test_missing_store_returns_empty_list(self, tmp_path):
        with patch("alarm_clock.STORE_PATH", tmp_path / "nonexistent.json"):
            assert load_alarms() == []

    def test_corrupt_store_returns_empty_list(self, tmp_path):
        store = tmp_path / "bad.json"
        store.write_text("not { valid } json >>>")
        with patch("alarm_clock.STORE_PATH", store):
            result = load_alarms()
        assert result == []

    def test_save_preserves_snoozed_until(self, tmp_path):
        snooze_dt = (datetime.now() + timedelta(minutes=5)).isoformat()
        alarms = [make_alarm(id="x", snoozed_until=snooze_dt)]
        store = tmp_path / "alarms.json"
        with patch("alarm_clock.STORE_PATH", store):
            save_alarms(alarms)
            loaded = load_alarms()
        assert loaded[0].snoozed_until == snooze_dt


# ─── AlarmMonitor: response channel ──────────────────────────────────────────

class TestAlarmMonitorChannel:

    def test_receive_response_sets_event(self):
        alarms: list[Alarm] = []
        lock = threading.Lock()
        monitor = AlarmMonitor(alarms, lock)

        assert not monitor._response_event.is_set()
        monitor.receive_response("s")
        assert monitor._response_event.is_set()
        assert monitor._response_value == "s"

    def test_stop_exits_run_loop(self):
        alarms: list[Alarm] = []
        lock = threading.Lock()
        monitor = AlarmMonitor(alarms, lock)
        monitor.start()
        monitor.stop()
        monitor.join(timeout=3)
        assert not monitor.is_alive()
