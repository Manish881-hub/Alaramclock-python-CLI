#!/usr/bin/env python3
"""
alarm_clock.py — A terminal alarm clock with persistent storage.

Design decisions documented in README.md.
"""

import json
import platform
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─── ANSI colours (skip on non-TTY so piped output stays clean) ───────────────

_COLOR = sys.stdout.isatty()
RED    = "\033[91m" if _COLOR else ""
GREEN  = "\033[92m" if _COLOR else ""
YELLOW = "\033[93m" if _COLOR else ""
CYAN   = "\033[96m" if _COLOR else ""
BOLD   = "\033[1m"  if _COLOR else ""
RESET  = "\033[0m"  if _COLOR else ""


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass
class Alarm:
    id: str
    label: str
    hour: int
    minute: int
    repeat_daily: bool
    active: bool = True
    snoozed_until: Optional[str] = None  # ISO-8601 datetime or None

    def next_trigger(self) -> Optional[datetime]:
        """Return the next datetime this alarm should fire, or None if it won't."""
        if not self.active:
            return None

        now = datetime.now()

        # Snooze takes priority over the normal schedule
        if self.snoozed_until:
            snooze_dt = datetime.fromisoformat(self.snoozed_until)
            if snooze_dt > now:
                return snooze_dt
            # Expired snooze — fall through to normal schedule

        candidate = now.replace(
            hour=self.hour, minute=self.minute, second=0, microsecond=0
        )
        if candidate <= now:
            if self.repeat_daily:
                candidate += timedelta(days=1)
            else:
                return None  # one-shot alarm already in the past

        return candidate

    @property
    def time_str(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def status_display(self) -> str:
        if not self.active:
            return f"{RED}off{RESET}"
        if self.snoozed_until:
            snooze_dt = datetime.fromisoformat(self.snoozed_until)
            remaining = int((snooze_dt - datetime.now()).total_seconds() / 60) + 1
            if remaining > 0:
                return f"{YELLOW}snoozed {remaining}m{RESET}"
        return f"{GREEN}active{RESET}"


# ─── Persistence ──────────────────────────────────────────────────────────────

STORE_PATH = Path.home() / ".alarms.json"


def load_alarms() -> list[Alarm]:
    if not STORE_PATH.exists():
        return []
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return [Alarm(**a) for a in data]
    except Exception:
        print(f"{YELLOW}⚠  Corrupt alarm store — starting fresh.{RESET}")
        return []


def save_alarms(alarms: list[Alarm]) -> None:
    STORE_PATH.write_text(
        json.dumps([asdict(a) for a in alarms], indent=2), encoding="utf-8"
    )


# ─── Cross-platform audio ─────────────────────────────────────────────────────

def beep() -> None:
    """Best-effort audio alert; degrades gracefully on all platforms."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Ping.aiff"],
                check=True, timeout=5, capture_output=True,
            )
            return
        if system == "Linux":
            for cmd in [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["aplay", "-q", "/usr/share/sounds/alsa/Front_Center.wav"],
            ]:
                if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                    subprocess.run(cmd, timeout=5, capture_output=True)
                    return
        if system == "Windows":
            import winsound
            for _ in range(3):
                winsound.Beep(880, 400)
                time.sleep(0.15)
            return
    except Exception:
        pass
    # Ultimate fallback: terminal bell character
    sys.stdout.write("\a\a\a")
    sys.stdout.flush()


# ─── Alarm monitor ────────────────────────────────────────────────────────────

SNOOZE_MINUTES      = 5
AUTO_DISMISS_SECS   = 30
POLL_INTERVAL_SECS  = 1
RING_REPEAT_SECS    = 5   # re-ring every N seconds until answered


class AlarmMonitor(threading.Thread):
    """
    Background daemon thread that polls once per second.
    Fires alarms within ±POLL_INTERVAL of their trigger time.

    User responses (s/d) are delivered via receive_response() from the main thread
    and picked up by the ringing alarm via a threading.Event — no busy-loop.
    """

    def __init__(self, alarms: list[Alarm], lock: threading.Lock) -> None:
        super().__init__(daemon=True, name="alarm-monitor")
        self.alarms = alarms
        self.lock = lock
        self._shutdown = threading.Event()
        # One-slot channel between main REPL thread and the currently-ringing alarm
        self._response_event = threading.Event()
        self._response_value: Optional[str] = None

    def stop(self) -> None:
        self._shutdown.set()

    def receive_response(self, value: str) -> None:
        """Called by the main REPL thread when the user types s or d."""
        self._response_value = value
        self._response_event.set()

    def run(self) -> None:
        while not self._shutdown.wait(timeout=POLL_INTERVAL_SECS):
            self._check_alarms()

    def _check_alarms(self) -> None:
        now = datetime.now()
        with self.lock:
            for alarm in self.alarms:
                nxt = alarm.next_trigger()
                if nxt and abs((nxt - now).total_seconds()) <= POLL_INTERVAL_SECS:
                    threading.Thread(
                        target=self._ring, args=(alarm,), daemon=True
                    ).start()

    def _ring(self, alarm: Alarm) -> None:
        self._response_event.clear()
        self._response_value = None

        banner = (
            f"\n{RED}{'━' * 52}{RESET}\n"
            f"  🔔  {BOLD}{alarm.label or 'Alarm'}{RESET}  —  {alarm.time_str}\n"
            f"{RED}{'━' * 52}{RESET}\n"
            f"  [{GREEN}s{RESET}] snooze {SNOOZE_MINUTES} min   [{GREEN}d{RESET}] dismiss\n"
        )

        deadline = time.monotonic() + AUTO_DISMISS_SECS
        while time.monotonic() < deadline:
            print(banner, flush=True)
            beep()
            # Block until user responds or the repeat interval expires
            answered = self._response_event.wait(timeout=RING_REPEAT_SECS)
            if answered:
                action = self._response_value
                self._response_event.clear()
                self._response_value = None
                with self.lock:
                    if action == "s":
                        alarm.snoozed_until = (
                            datetime.now() + timedelta(minutes=SNOOZE_MINUTES)
                        ).isoformat()
                        save_alarms(self.alarms)
                        print(f"\n{YELLOW}  Snoozed for {SNOOZE_MINUTES} min.{RESET}\n")
                    elif action == "d":
                        self._dismiss(alarm)
                        print(f"\n{GREEN}  Alarm dismissed.{RESET}\n")
                return  # always return after a response

        # Auto-dismiss after AUTO_DISMISS_SECS
        with self.lock:
            self._dismiss(alarm)
        print(f"\n{YELLOW}  '{alarm.label}' auto-dismissed.{RESET}\n")

    def _dismiss(self, alarm: Alarm) -> None:
        """Mark one-shot alarms inactive; clear snooze for daily alarms."""
        alarm.snoozed_until = None
        if not alarm.repeat_daily:
            alarm.active = False
        save_alarms(self.alarms)


# ─── CLI helpers ──────────────────────────────────────────────────────────────

HELP_TEXT = f"""
{BOLD}Commands{RESET}
  {GREEN}add{RESET}           Add a new alarm
  {GREEN}list{RESET}          Show all alarms
  {GREEN}delete <n>{RESET}    Delete alarm by list number
  {GREEN}enable <n>{RESET}    Re-enable a disabled alarm
  {GREEN}quit{RESET}          Exit  (alarms persist automatically)
  {GREEN}help{RESET}          Show this message

{BOLD}While an alarm is ringing{RESET}
  {GREEN}s{RESET}             Snooze {SNOOZE_MINUTES} minutes
  {GREEN}d{RESET}             Dismiss
"""


def parse_time(s: str) -> tuple[int, int]:
    """Parse 'HH:MM' → (hour, minute). Raises ValueError on bad input."""
    parts = s.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected HH:MM, got '{s}'")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Time out of range: {h}:{m:02d}")
    return h, m


def show_alarms(alarms: list[Alarm]) -> None:
    if not alarms:
        print(f"  {YELLOW}No alarms set — use 'add' to create one.{RESET}\n")
        return
    header = f"  {'#':>3}  {'TIME':>5}  {'LABEL':<22}  {'REPEAT':<7}  STATUS"
    sep    = f"  {'─'*3}  {'─'*5}  {'─'*22}  {'─'*7}  {'─'*12}"
    print(f"\n{header}\n{sep}")
    for i, a in enumerate(alarms, 1):
        repeat = "daily" if a.repeat_daily else "once"
        print(f"  {i:>3}  {a.time_str:>5}  {a.label:<22}  {repeat:<7}  {a.status_display}")
    print()


def prompt(text: str) -> str:
    return input(f"{CYAN}{text}{RESET}").strip()


# ─── Main REPL ────────────────────────────────────────────────────────────────

def main() -> None:
    alarms = load_alarms()
    lock = threading.Lock()

    monitor = AlarmMonitor(alarms, lock)
    monitor.start()

    print(f"\n{BOLD}{CYAN}⏰  Alarm Clock{RESET}  (type {GREEN}help{RESET} for commands)\n")
    if alarms:
        show_alarms(alarms)

    while True:
        try:
            raw = prompt("› ")
        except (EOFError, KeyboardInterrupt):
            break

        parts = raw.lower().split()

        # Single-char responses forwarded to the ringing alarm thread
        if raw.lower() in ("s", "d"):
            monitor.receive_response(raw.lower())
            continue

        if not parts:
            continue

        verb = parts[0]

        # ── quit ──────────────────────────────────────────────────────────────
        if verb in ("quit", "q", "exit"):
            break

        # ── help ──────────────────────────────────────────────────────────────
        elif verb == "help":
            print(HELP_TEXT)

        # ── add ───────────────────────────────────────────────────────────────
        elif verb == "add":
            try:
                time_raw = prompt("  Time (HH:MM): ")
                h, m = parse_time(time_raw)
                label = prompt("  Label (optional): ") or "Alarm"
                repeat = prompt("  Repeat daily? (y/N): ").lower() in ("y", "yes")

                alarm = Alarm(
                    id=str(uuid.uuid4()),
                    label=label,
                    hour=h,
                    minute=m,
                    repeat_daily=repeat,
                )
                with lock:
                    alarms.append(alarm)
                    save_alarms(alarms)

                nxt = alarm.next_trigger()
                when = nxt.strftime("%a %d %b %H:%M") if nxt else "never"
                print(f"\n  {GREEN}✓  '{label}' set — next ring {when}{RESET}\n")

            except ValueError as e:
                print(f"  {RED}Error: {e}.{RESET}\n")
            except EOFError:
                break

        # ── list ──────────────────────────────────────────────────────────────
        elif verb == "list":
            with lock:
                show_alarms(alarms)

        # ── delete ────────────────────────────────────────────────────────────
        elif verb in ("delete", "del", "rm"):
            try:
                idx = int(parts[1]) - 1
                with lock:
                    if 0 <= idx < len(alarms):
                        removed = alarms.pop(idx)
                        save_alarms(alarms)
                        print(f"  {GREEN}✓  Deleted '{removed.label}'{RESET}\n")
                    else:
                        print(f"  {RED}No alarm #{int(parts[1])}.{RESET}\n")
            except (IndexError, ValueError):
                print(f"  {RED}Usage: delete <n>  (use 'list' to see numbers){RESET}\n")

        # ── enable ────────────────────────────────────────────────────────────
        elif verb in ("enable", "on"):
            try:
                idx = int(parts[1]) - 1
                with lock:
                    if 0 <= idx < len(alarms):
                        alarms[idx].active = True
                        alarms[idx].snoozed_until = None
                        save_alarms(alarms)
                        print(f"  {GREEN}✓  Alarm #{int(parts[1])} re-enabled{RESET}\n")
                    else:
                        print(f"  {RED}No alarm #{int(parts[1])}.{RESET}\n")
            except (IndexError, ValueError):
                print(f"  {RED}Usage: enable <n>  (use 'list' to see numbers){RESET}\n")

        # ── unknown ───────────────────────────────────────────────────────────
        else:
            print(f"  {YELLOW}Unknown command '{verb}'. Type 'help'.{RESET}\n")

    monitor.stop()
    print(f"\n{CYAN}Goodbye. Alarms saved to {STORE_PATH}{RESET}\n")


if __name__ == "__main__":
    main()
