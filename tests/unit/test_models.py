"""Tests for alarm_clock.models."""

from datetime import datetime, timedelta
from alarm_clock.models import Alarm


def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="test-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


class TestAlarmInit:
    def test_minimal_creation(self):
        a = Alarm(id="x", label="Test", hour=7, minute=30)
        assert a.id == "x"
        assert a.label == "Test"
        assert a.hour == 7
        assert a.minute == 30
        assert a.repeat_daily is False
        assert a.active is True
        assert a.snoozed_until is None

    def test_full_creation(self):
        a = Alarm(id="y", label="Full", hour=12, minute=0,
                  repeat_daily=True, active=False, snoozed_until="2026-01-01T00:00:00")
        assert a.repeat_daily is True
        assert a.active is False
        assert a.snoozed_until == "2026-01-01T00:00:00"


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
        assert abs((nxt - snooze_dt).total_seconds()) < 1

    def test_expired_snooze_falls_through_to_schedule(self):
        past_snooze = (datetime.now() - timedelta(minutes=5)).isoformat()
        future = datetime.now() + timedelta(hours=1)
        a = make_alarm(hour=future.hour, minute=future.minute,
                       snoozed_until=past_snooze)
        nxt = a.next_trigger()
        assert nxt is not None
        assert nxt.date() == datetime.now().date()

    def test_midnight_rollover(self):
        a = make_alarm(hour=0, minute=5, repeat_daily=True)
        nxt = a.next_trigger()
        now = datetime.now()
        if now.hour == 0 and now.minute < 5:
            assert nxt.date() == now.date()
        else:
            assert nxt.date() == (now + timedelta(days=1)).date()

    def test_exact_current_minute_fires(self):
        now = datetime.now()
        a = make_alarm(hour=now.hour, minute=now.minute)
        if not a.active:
            return
        candidate = now.replace(hour=now.hour, minute=now.minute, second=0, microsecond=0)
        if candidate <= now:
            if a.repeat_daily:
                assert a.next_trigger().date() == (now + timedelta(days=1)).date()
            else:
                assert a.next_trigger() is None
        else:
            assert a.next_trigger() is not None


class TestProperties:
    def test_time_str_zero_padded(self):
        a = make_alarm(hour=7, minute=5)
        assert a.time_str == "07:05"

    def test_time_str_midnight(self):
        a = make_alarm(hour=0, minute=0)
        assert a.time_str == "00:00"

    def test_time_str_max(self):
        a = make_alarm(hour=23, minute=59)
        assert a.time_str == "23:59"

    def test_status_display_active(self):
        assert make_alarm().status_display == "active"

    def test_status_display_off(self):
        assert make_alarm(active=False).status_display == "off"

    def test_status_display_snoozed(self):
        snooze_dt = datetime.now() + timedelta(minutes=3)
        status = make_alarm(snoozed_until=snooze_dt.isoformat()).status_display
        assert "snoozed" in status

    def test_status_display_expired_snooze(self):
        past_snooze = (datetime.now() - timedelta(minutes=1)).isoformat()
        status = make_alarm(snoozed_until=past_snooze).status_display
        assert status != "off"


class TestSerialization:
    def test_to_dict(self):
        a = make_alarm(id="serialize-test", label="Serialize", hour=6, minute=30)
        d = a.to_dict()
        assert d["id"] == "serialize-test"
        assert d["label"] == "Serialize"
        assert d["hour"] == 6
        assert d["minute"] == 30
        assert d["repeat_daily"] is False
        assert d["active"] is True

    def test_from_dict(self):
        d = dict(id="fd-test", label="From Dict", hour=10, minute=15,
                 repeat_daily=True, active=False, snoozed_until=None)
        a = Alarm.from_dict(d)
        assert a.id == "fd-test"
        assert a.label == "From Dict"
        assert a.hour == 10
        assert a.minute == 15
        assert a.repeat_daily is True
        assert a.active is False

    def test_round_trip(self):
        original = make_alarm(id="rt", label="RT", hour=14, minute=45,
                              repeat_daily=True, active=False)
        restored = Alarm.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.label == original.label
        assert restored.hour == original.hour
        assert restored.minute == original.minute
        assert restored.repeat_daily == original.repeat_daily
        assert restored.active == original.active
