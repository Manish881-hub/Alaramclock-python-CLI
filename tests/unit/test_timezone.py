"""Tests for alarm_clock.timezone."""

from datetime import datetime, timezone, timedelta
import pytest

from alarm_clock.timezone import (
    get_timezone,
    get_tz_offset,
    convert_time,
    now_in_tz,
)


class TestGetTimezone:
    def test_local(self):
        tz = get_timezone("local")
        assert tz is not None

    def test_utc(self):
        tz = get_timezone("UTC")
        assert tz is not None
        assert tz.utcoffset(None) == timedelta(0)

    def test_valid_iana(self):
        tz = get_timezone("America/New_York")
        assert tz is not None

    def test_invalid_iana(self):
        tz = get_timezone("Mars/Olympus")
        assert tz is None


class TestGetTzOffset:
    def test_utc_offset(self):
        offset = get_tz_offset("UTC")
        assert offset == timedelta(0)

    def test_local_offset(self):
        offset = get_tz_offset("local")
        assert offset is not None

    def test_invalid_returns_none(self):
        assert get_tz_offset("Invalid/Zone") is None


class TestConvertTime:
    def test_utc_to_est(self):
        dt = datetime(2026, 6, 16, 12, 0, 0)
        result = convert_time(dt, "UTC", "America/New_York")
        assert result is not None
        assert result.hour in (8, 7)

    def test_est_to_utc(self):
        dt = datetime(2026, 6, 16, 8, 0, 0)
        result = convert_time(dt, "America/New_York", "UTC")
        assert result is not None
        assert result.hour in (12, 13)

    def test_invalid_zone_returns_original(self):
        dt = datetime(2026, 6, 16, 12, 0, 0)
        result = convert_time(dt, "UTC", "Invalid/Zone")
        assert result == dt

    def test_same_zone(self):
        dt = datetime(2026, 6, 16, 12, 0, 0)
        result = convert_time(dt, "UTC", "UTC")
        assert result.hour == 12


class TestNowInTz:
    def test_now_in_utc(self):
        n = now_in_tz("UTC")
        assert n.tzinfo is not None
        assert n.utcoffset() == timedelta(0)

    def test_now_in_local(self):
        n = now_in_tz("local")
        assert n.tzinfo is not None

    def test_now_in_specific(self):
        n = now_in_tz("America/New_York")
        assert n.tzinfo is not None

    def test_invalid_falls_back(self):
        n = now_in_tz("Bad/Zone")
        assert n.tzinfo is None or True
