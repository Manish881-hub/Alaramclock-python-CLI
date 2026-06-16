"""Rich TUI for alarm clock."""

import threading
import time
from collections.abc import Callable

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from alarm_clock.config import Config
from alarm_clock.logging_conf import get_logger
from alarm_clock.models import Alarm

logger = get_logger(__name__)


class AlarmTUI:
    """Rich-based Terminal User Interface."""

    def __init__(
        self,
        config: Config,
        alarms: list[Alarm],
        lock: threading.Lock,
        on_add: Callable[[str, int, int, bool], None],
        on_delete: Callable[[int], None],
        on_toggle: Callable[[int], None],
        on_snooze: Callable[[Alarm], None],
        on_dismiss: Callable[[Alarm], None],
        on_quit: Callable[[], None],
    ):
        self.config = config
        self.alarms = alarms
        self.lock = lock
        self.on_add = on_add
        self.on_delete = on_delete
        self.on_toggle = on_toggle
        self.on_snooze = on_snooze
        self.on_dismiss = on_dismiss
        self.on_quit = on_quit

        self.console = Console()
        self.layout = Layout()
        self._ringing_alarm: Alarm | None = None
        self._ring_event = threading.Event()
        self._running = True
        self._selected_index = 0

        self._setup_layout()

    def _setup_layout(self) -> None:
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5),
        )
        self.layout["main"].split_row(
            Layout(name="alarms", ratio=3),
            Layout(name="help", ratio=1),
        )

    def _make_header(self) -> Panel:
        return Panel(
            Align.center("[bold cyan]⏰ Alarm Clock[/bold cyan]"),
            style="cyan",
        )

    def _make_alarms_table(self) -> Table:
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("TIME", justify="center", width=6)
        table.add_column("LABEL", ratio=1)
        table.add_column("REPEAT", justify="center", width=7)
        table.add_column("STATUS", justify="center", width=12)

        with self.lock:
            for i, alarm in enumerate(self.alarms):
                repeat = "daily" if alarm.repeat_daily else "once"
                status = alarm.status_display
                style = ""
                if not alarm.active:
                    style = "red"
                elif "snoozed" in status:
                    style = "yellow"
                else:
                    style = "green"

                row_style = style if i == self._selected_index else ""
                table.add_row(
                    str(i + 1),
                    alarm.time_str,
                    alarm.label or "—",
                    repeat,
                    f"[{style}]{status}[/{style}]",
                    style=row_style,
                )

        return table

    def _make_help(self) -> Panel:
        help_text = Text()
        help_text.append("Keys:\n", style="bold")
        help_text.append("  ↑/↓ or j/k  ", style="cyan")
        help_text.append("Navigate\n")
        help_text.append("  a           ", style="cyan")
        help_text.append("Add alarm\n")
        help_text.append("  d/Del       ", style="cyan")
        help_text.append("Delete alarm\n")
        help_text.append("  Space/Enter ", style="cyan")
        help_text.append("Toggle on/off\n")
        help_text.append("  s           ", style="cyan")
        help_text.append("Snooze (ringing)\n")
        help_text.append("  d           ", style="cyan")
        help_text.append("Dismiss (ringing)\n")
        help_text.append("  q/Ctrl+C    ", style="cyan")
        help_text.append("Quit")

        return Panel(help_text, title="Help", border_style="blue")

    def _make_footer(self) -> Panel:
        if self._ringing_alarm:
            text = Text()
            text.append(f"🔔 {self._ringing_alarm.label} — ", style="bold red")
            text.append(self._ringing_alarm.time_str, style="bold")
            text.append("  [s] Snooze  [d] Dismiss", style="yellow")
            return Panel(Align.center(text), border_style="red", style="red")
        return Panel(
            Align.center("[dim]Press 'a' to add alarm, 'q' to quit[/dim]"),
            style="dim",
        )

    def _update_layout(self) -> None:
        self.layout["header"].update(self._make_header())
        self.layout["alarms"].update(
            Panel(self._make_alarms_table(), title="Alarms", border_style="green")
        )
        self.layout["help"].update(self._make_help())
        self.layout["footer"].update(self._make_footer())

    def start_ring(self, alarm: Alarm) -> None:
        """Signal that an alarm is ringing."""
        self._ringing_alarm = alarm
        self._ring_event.set()

    def stop_ring(self) -> None:
        """Signal that ringing has stopped."""
        self._ringing_alarm = None
        self._ring_event.clear()

    def run(self) -> None:
        """Run the TUI event loop."""
        self._update_layout()
        with Live(self.layout, console=self.console, refresh_per_second=2, screen=True) as live:
            while self._running:
                self._update_layout()
                live.update(self.layout)

                # Check for key input (non-blocking)
                if self.console.is_terminal:
                    try:
                        key = self.console.input("")  # type: ignore[call-arg]
                        self._handle_key(key)
                    except Exception:
                        pass

                time.sleep(0.1)

    def _handle_key(self, key: str) -> None:
        key = key.lower().strip()
        if not key:
            return

        if key in ("q", "ctrl+c"):
            self._running = False
            self.on_quit()
            return

        if self._ringing_alarm:
            if key == "s":
                self.on_snooze(self._ringing_alarm)
                return
            if key == "d":
                self.on_dismiss(self._ringing_alarm)
                return

        with self.lock:
            count = len(self.alarms)

        if key in ("up", "k"):
            self._selected_index = max(0, self._selected_index - 1)
        elif key in ("down", "j"):
            self._selected_index = min(count - 1, self._selected_index + 1)
        elif key == "a":
            self._prompt_add_alarm()
        elif key in ("d", "delete"):
            if count > 0:
                self.on_delete(self._selected_index)
                self._selected_index = min(self._selected_index, count - 2)
        elif key in (" ", "enter") and count > 0:
            self.on_toggle(self._selected_index)

    def _prompt_add_alarm(self) -> None:
        """Prompt for new alarm details."""
        self.console.clear()
        self.console.print("[bold]Add New Alarm[/bold]\n")

        time_str = Prompt.ask("Time (HH:MM)", default="07:00")
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            self.console.print("[red]Invalid time format[/red]")
            time.sleep(1)
            return

        label = Prompt.ask("Label (optional)", default="Alarm")
        repeat = Prompt.ask("Repeat daily? (y/N)", default="n").lower() in ("y", "yes")

        self.on_add(label, hour, minute, repeat)
