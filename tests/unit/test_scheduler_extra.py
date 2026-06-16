"""Additional scheduler tests for uncovered paths."""

import threading
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from alarm_clock.config import Config
from alarm_clock.models import Alarm
from alarm_clock.scheduler import AlarmMonitor


def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="test-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


class TestAlarmMonitorCheck:
    def test_check_alarms_ignores_none_trigger(self):
        config = Config()
        alarms = [make_alarm(id="x", active=False)]
        lock = threading.Lock()
        callback = MagicMock()
        monitor = AlarmMonitor(config, alarms, lock, callback)
        monitor._check_alarms()
        callback.assert_not_called()

    def test_check_alarms_no_due(self):
        config = Config()
        future = datetime.now() + timedelta(days=1)
        alarms = [make_alarm(id="y", hour=future.hour, minute=future.minute)]
        lock = threading.Lock()
        callback = MagicMock()
        monitor = AlarmMonitor(config, alarms, lock, callback)
        monitor._check_alarms()
        callback.assert_not_called()
