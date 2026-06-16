"""Alarm scheduler with background monitoring thread."""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from alarm_clock.config import Config
from alarm_clock.logging_conf import get_logger
from alarm_clock.models import Alarm
from alarm_clock.storage import save_alarms

logger = get_logger(__name__)

SNOOZE_MINUTES = 5
AUTO_DISMISS_SECS = 30
POLL_INTERVAL_SECS = 1
RING_REPEAT_SECS = 5


class AlarmMonitor(threading.Thread):
    """Background daemon thread that polls for due alarms."""

    def __init__(
        self,
        config: Config,
        alarms: list[Alarm],
        lock: threading.Lock,
        ring_callback: Callable[[Alarm], None],
    ) -> None:
        super().__init__(daemon=True, name="alarm-monitor")
        self.config = config
        self.alarms = alarms
        self.lock = lock
        self._ring_callback = ring_callback
        self._shutdown = threading.Event()

        gen_cfg = config.general
        self._poll_interval = gen_cfg.poll_interval_seconds
        self._snooze_minutes = gen_cfg.snooze_minutes
        self._auto_dismiss = gen_cfg.auto_dismiss_seconds
        self._ring_repeat = gen_cfg.ring_repeat_seconds

    def stop(self) -> None:
        self._shutdown.set()

    def run(self) -> None:
        logger.info("Alarm monitor started")
        while not self._shutdown.wait(timeout=self._poll_interval):
            self._check_alarms()
        logger.info("Alarm monitor stopped")

    def _check_alarms(self) -> None:
        now = datetime.now()
        with self.lock:
            for alarm in self.alarms:
                nxt = alarm.next_trigger()
                if nxt and abs((nxt - now).total_seconds()) <= self._poll_interval:
                    logger.info("Alarm due: {} ({})", alarm.label, alarm.time_str)
                    threading.Thread(
                        target=self._ring_callback,
                        args=(alarm,),
                        daemon=True,
                    ).start()

    def snooze_alarm(self, alarm: Alarm) -> None:
        """Snooze an alarm for configured minutes."""
        snooze_until = datetime.now() + timedelta(minutes=self._snooze_minutes)
        with self.lock:
            alarm.snoozed_until = snooze_until.isoformat()
            save_alarms(self.config, self.alarms)
        logger.info("Snoozed '{}' until {}", alarm.label, snooze_until.strftime("%H:%M"))

    def dismiss_alarm(self, alarm: Alarm) -> None:
        """Dismiss an alarm - disable one-shot, clear snooze for daily."""
        with self.lock:
            alarm.snoozed_until = None
            if not alarm.repeat_daily:
                alarm.active = False
            save_alarms(self.config, self.alarms)
        logger.info("Dismissed '{}'", alarm.label)
