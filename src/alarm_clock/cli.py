"""Typer CLI entry point for alarm clock."""

import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from alarm_clock import __version__
from alarm_clock.audio import AudioPlayer
from alarm_clock.config import Config
from alarm_clock.logging_conf import get_logger, setup_logging
from alarm_clock.models import Alarm
from alarm_clock.scheduler import AlarmMonitor
from alarm_clock.service import (
    install_service,
    run_daemon,
    uninstall_service,
)
from alarm_clock.storage import load_alarms, save_alarms

app = typer.Typer(
    name="alarm-clock",
    help="Production-ready terminal alarm clock with persistence, TUI, and system service support",
    no_args_is_help=True,
)

console = Console()
logger = get_logger(__name__)


def _get_config(config_path: Path | None = None) -> Config:
    config = Config.load(config_path)
    setup_logging(config)
    return config


def _parse_time(time_str: str) -> tuple[int, int]:
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise typer.BadParameter(f"Expected HH:MM, got '{time_str}'")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise typer.BadParameter(f"Time out of range: {h}:{m:02d}")
    return h, m


def _display_alarms(alarms: list[Alarm]) -> None:
    if not alarms:
        rprint("[yellow]No alarms set.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="dim", width=8)
    table.add_column("TIME", justify="center", width=6)
    table.add_column("LABEL", ratio=1)
    table.add_column("REPEAT", justify="center", width=7)
    table.add_column("STATUS", justify="center", width=12)

    for i, alarm in enumerate(alarms, 1):
        repeat = "daily" if alarm.repeat_daily else "once"
        status = alarm.status_display
        style = ""
        if not alarm.active:
            style = "red"
        elif "snoozed" in status:
            style = "yellow"
        else:
            style = "green"

        table.add_row(
            str(i),
            alarm.id[:8],
            alarm.time_str,
            alarm.label or "—",
            repeat,
            f"[{style}]{status}[/{style}]",
        )

    console.print(table)


@app.command("list")
def list_alarms(
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """List all alarms."""
    config = _get_config(config_path)
    alarms = load_alarms(config)
    _display_alarms(alarms)


@app.command()
def add(
    time: str = typer.Argument(..., help="Time in HH:MM format"),
    label: str = typer.Option("Alarm", "--label", "-l", help="Alarm label"),
    repeat: bool = typer.Option(False, "--repeat", "-r", help="Repeat daily"),
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Add a new alarm."""
    config = _get_config(config_path)
    alarms = load_alarms(config)
    lock = threading.Lock()

    try:
        hour, minute = _parse_time(time)
    except typer.BadParameter as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e

    alarm = Alarm(
        id=str(uuid.uuid4()),
        label=label,
        hour=hour,
        minute=minute,
        repeat_daily=repeat,
    )

    with lock:
        alarms.append(alarm)
        save_alarms(config, alarms)

    nxt = alarm.next_trigger()
    when = nxt.strftime("%a %d %b %H:%M") if nxt else "never"
    rprint(f"[green]Alarm '{label}' set — next ring {when}[/green]")


@app.command()
def delete(
    alarm_id: str = typer.Argument(..., help="Alarm number (from list) or ID prefix"),
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Delete an alarm by number or ID prefix."""
    config = _get_config(config_path)
    alarms = load_alarms(config)
    lock = threading.Lock()

    with lock:
        idx = _resolve_alarm(alarm_id, alarms)
        if idx is None:
            rprint(f"[red]No alarm matching '{alarm_id}'[/red]")
            raise typer.Exit(1)
        removed = alarms.pop(idx)
        save_alarms(config, alarms)

    rprint(f"[green]Deleted alarm '{removed.label}' ({removed.time_str})[/green]")


@app.command()
def enable(
    alarm_id: str = typer.Argument(..., help="Alarm number (from list) or ID prefix"),
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Enable a disabled alarm."""
    config = _get_config(config_path)
    alarms = load_alarms(config)
    lock = threading.Lock()

    with lock:
        idx = _resolve_alarm(alarm_id, alarms)
        if idx is None:
            rprint(f"[red]No alarm matching '{alarm_id}'[/red]")
            raise typer.Exit(1)
        alarms[idx].active = True
        alarms[idx].snoozed_until = None
        save_alarms(config, alarms)

    rprint(f"[green]Alarm #{alarm_id} enabled[/green]")


@app.command()
def daemon(
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Run alarm clock as background daemon."""
    config = _get_config(config_path)
    alarms = load_alarms(config)
    lock = threading.Lock()
    audio_player = AudioPlayer(config)

    def ring_callback(alarm: Alarm) -> None:
        audio_player.play(repeat=1)

    monitor = AlarmMonitor(config, alarms, lock, ring_callback)
    run_daemon(config, alarms, lock, audio_player, monitor)


@app.command()
def tui(  # pragma: no cover (interactive)
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Launch the Rich TUI for interactive alarm management."""
    config = _get_config(config_path)
    alarms = load_alarms(config)
    lock = threading.Lock()

    def on_add(label: str, hour: int, minute: int, repeat: bool) -> None:
        nonlocal alarms
        alarm = Alarm(
            id=str(uuid.uuid4()),
            label=label,
            hour=hour,
            minute=minute,
            repeat_daily=repeat,
        )
        with lock:
            alarms.append(alarm)
            save_alarms(config, alarms)
        logger.info("Added alarm '{}' at {}", label, alarm.time_str)

    def on_delete(index: int) -> None:
        nonlocal alarms
        with lock:
            if 0 <= index < len(alarms):
                removed = alarms.pop(index)
                save_alarms(config, alarms)
                logger.info("Deleted alarm '{}'", removed.label)

    def on_toggle(index: int) -> None:
        nonlocal alarms
        with lock:
            if 0 <= index < len(alarms):
                a = alarms[index]
                a.active = not a.active
                if a.active:
                    a.snoozed_until = None
                save_alarms(config, alarms)
                logger.info(
                    "Toggled alarm '{}' to {}", a.label, "active" if a.active else "inactive"
                )

    def on_snooze(alarm: Alarm) -> None:
        snooze_until = datetime.now() + timedelta(minutes=config.general.snooze_minutes)
        with lock:
            alarm.snoozed_until = snooze_until.isoformat()
            save_alarms(config, alarms)
        logger.info("Snoozed '{}'", alarm.label)

    def on_dismiss(alarm: Alarm) -> None:
        with lock:
            alarm.snoozed_until = None
            if not alarm.repeat_daily:
                alarm.active = False
            save_alarms(config, alarms)
        logger.info("Dismissed '{}'", alarm.label)

    def on_quit() -> None:
        logger.info("TUI shutting down")

    from alarm_clock.tui import AlarmTUI

    monitor = AlarmMonitor(config, alarms, lock, lambda a: None)
    monitor.start()

    ui = AlarmTUI(
        config, alarms, lock, on_add, on_delete, on_toggle, on_snooze, on_dismiss, on_quit
    )

    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()


@app.command()
def install(
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Install alarm clock as a system service."""
    _get_config(config_path)
    if install_service():
        rprint("[green]Service installed successfully[/green]")
    else:
        rprint("[red]Service installation failed[/red]")
        raise typer.Exit(1)


@app.command()
def uninstall(
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Uninstall alarm clock system service."""
    _get_config(config_path)
    if uninstall_service():
        rprint("[green]Service uninstalled successfully[/green]")
    else:
        rprint("[red]Service uninstallation failed[/red]")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    rprint(f"[bold cyan]alarm-clock[/bold cyan] v{__version__}")


@app.callback()
def main_callback(
    ctx: typer.Context,
) -> None:
    """Alarm Clock — manage alarms from the terminal."""
    pass


def _resolve_alarm(alarm_id: str, alarms: list[Alarm]) -> int | None:
    """Resolve an alarm by number (1-indexed) or by ID prefix."""
    try:
        idx = int(alarm_id) - 1
        if 0 <= idx < len(alarms):
            return idx
    except ValueError:
        for i, a in enumerate(alarms):
            if a.id.startswith(alarm_id):
                return i
    return None


if __name__ == "__main__":
    app()
