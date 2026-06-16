"""Timezone utilities using zoneinfo (stdlib 3.9+)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_timezone(tz_name: str) -> Optional[timezone]:
    """Get timezone object from name."""
    if tz_name == "local":
        return datetime.now().astimezone().tzinfo
    if tz_name == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return None


def get_tz_offset(tz_name: str) -> Optional[timedelta]:
    """Get current UTC offset for timezone."""
    tz = get_timezone(tz_name)
    if tz is None:
        return None
    return datetime.now(tz).utcoffset() or timedelta(0)


def convert_time(local_dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """Convert datetime from one timezone to another."""
    from_zone = get_timezone(from_tz)
    to_zone = get_timezone(to_z)
    if from_zone is None or to_zone is None:
        return local_dt
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(tzinfo=from_zone)
    return local_dt.astimezone(to_zone)


def now_in_tz(tz_name: str) -> datetime:
    """Get current time in specified timezone."""
    tz = get_timezone(tz_name)
    if tz is None:
        return datetime.now()
    return datetime.now(tz)