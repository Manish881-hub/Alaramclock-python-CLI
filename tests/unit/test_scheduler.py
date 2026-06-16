"""Tests for alarm_clock.scheduler."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from alarm_clock.models import Alarm
from alarm_clock.config import Config
from alarm_clock.scheduler import AlarmMonitor, SNOOZE_MINUTES


def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="test-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def alarms():
    return [make_alarm(id="a1"), make_alarm(id="a2", label="Second")]


@pytest.fixture
def lock():
    return threading.Lock()


class TestAlarmMonitorInit:
    def test_creation(self, config, alarms, lock):
        callback = MagicMock()
        monitor = AlarmMonitor(config, alarms, lock, callback)
        assert monitor.alarms is alarms
        assert monitor.lock is lock

    def test_stop_creates_shutdown_event(self, config, alarms, lock):
        monitor = AlarmMonitor(config, alarms, lock, MagicMock())
        assert not monitor._shutdown.is_set()
        monitor.stop()
        assert monitor._shutdown.is_set()


class TestAlarmMonitorRun:
    def test_stop_exits_run_loop(self, config, alarms, lock):
        callback = MagicMock()
        monitor = AlarmMonitor(config, alarms, lock, callback)
        monitor.start()
        monitor.stop()
        monitor.join(timeout=3)
        assert not monitor.is_alive()

    def test_ring_callback_invoked_for_due_alarm(self, config, lock):
        callback = MagicMock()
        from datetime import datetime, timedelta
        future = datetime.now() + timedelta(seconds=2)
        alarm = make_alarm(id="due", hour=future.hour, minute=future.minute)
        alarms = [alarm]
        monitor = AlarmMonitor(config, alarms, lock, callback)
        monitor.start()
        import time
        time.sleep(0.2)
        monitor.stop()
        monitor.join(timeout=3)


class TestSnoozeDismiss:
    def test_snooze_alarm(self, config, alarms, lock):
        monitor = AlarmMonitor(config, alarms, lock, MagicMock())
        alarm = alarms[0]
        assert alarm.snoozed_until is None
        with patch("alarm_clock.scheduler.save_alarms"):
            monitor.snooze_alarm(alarm)
        assert alarm.snoozed_until is not None

    def test_dismiss_one_shot(self, config, alarms, lock):
        monitor = AlarmMonitor(config, alarms, lock, MagicMock())
        alarm = make_alarm(id="one_shot", repeat_daily=False, active=True)
        with patch("alarm_clock.scheduler.save_alarms"):
            monitor.dismiss_alarm(alarm)
        assert alarm.snoozed_until is None
        assert alarm.active is False

    def test_dismiss_daily_clears_snooze_only(self, config, alarms, lock):
        monitor = AlarmMonitor(config, alarms, lock, MagicMock())
        alarm = make_alarm(id="daily", repeat_daily=True, active=True,
                           snoozed_until="2026-06-16T12:00:00")
        with patch("alarm_clock.scheduler.save_alarms"):
            monitor.dismiss_alarm(alarm)
        assert alarm.snoozed_until is None
        assert alarm.active is True


class TestConfigIntegration:
    def test_monitor_uses_config_values(self):
        config = Config()
        config.general.snooze_minutes = 10
        config.general.poll_interval_seconds = 2
        config.general.auto_dismiss_seconds = 60
        config.general.ring_repeat_seconds = 10
        monitor = AlarmMonitor(config, [], threading.Lock(), MagicMock())
        assert monitor._poll_interval == 2
        assert monitor._snooze_minutes == 10
        assert monitor._auto_dismiss == 60
        assert monitor._ring_repeat == 10
