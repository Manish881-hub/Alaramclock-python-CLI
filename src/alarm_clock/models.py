"""Data models for alarm clock."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta


@dataclass
class Alarm:
    """Represents a single alarm with scheduling logic."""

    id: str
    label: str
    hour: int
    minute: int
    repeat_daily: bool = False
    active: bool = True
    snoozed_until: str | None = None  # ISO-8601 datetime or None

    def next_trigger(self, tz_offset: timedelta | None = None) -> datetime | None:
        """Return the next datetime this alarm should fire, or None if it won't."""
        if not self.active:
            return None

        now = datetime.now()
        if tz_offset:
            now = now + tz_offset

        if self.snoozed_until:
            snooze_dt = datetime.fromisoformat(self.snoozed_until)
            if snooze_dt > now:
                return snooze_dt
            # Expired snooze — fall through to normal schedule

        candidate = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if candidate <= now:
            if self.repeat_daily:
                candidate += timedelta(days=1)
            else:
                return None

        return candidate

    @property
    def time_str(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def status_display(self) -> str:
        if not self.active:
            return "off"
        if self.snoozed_until:
            snooze_dt = datetime.fromisoformat(self.snoozed_until)
            remaining = int((snooze_dt - datetime.now()).total_seconds() / 60) + 1
            if remaining > 0:
                return f"snoozed {remaining}m"
        return "active"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        return cls(**data)
