"""Tests for alarm_clock.cli."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from alarm_clock.cli import app, _parse_time, _resolve_alarm
from alarm_clock.models import Alarm

runner = CliRunner()


def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="test-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


class TestParseTime:
    def test_valid(self):
        assert _parse_time("07:30") == (7, 30)
        assert _parse_time("00:00") == (0, 0)
        assert _parse_time("23:59") == (23, 59)

    def test_invalid_format(self):
        import typer
        try:
            _parse_time("730")
            assert False, "Should raise"
        except typer.BadParameter:
            pass

    def test_out_of_range(self):
        import typer
        try:
            _parse_time("24:00")
            assert False, "Should raise"
        except typer.BadParameter:
            pass


class TestResolveAlarm:
    def test_by_number(self):
        alarms = [make_alarm(id="abc"), make_alarm(id="def")]
        assert _resolve_alarm("1", alarms) == 0
        assert _resolve_alarm("2", alarms) == 1

    def test_by_id_prefix(self):
        alarms = [make_alarm(id="abc123"), make_alarm(id="def456")]
        assert _resolve_alarm("abc", alarms) == 0
        assert _resolve_alarm("def", alarms) == 1

    def test_not_found(self):
        alarms = [make_alarm(id="abc")]
        assert _resolve_alarm("999", alarms) is None
        assert _resolve_alarm("xyz", alarms) is None

    def test_empty_list(self):
        assert _resolve_alarm("1", []) is None


class TestCLIVersion:
    def test_version(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "alarm-clock" in result.stdout


class TestCLIList:
    def test_list_empty(self):
        with patch("alarm_clock.cli.load_alarms", return_value=[]):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "No alarms" in result.stdout

    def test_list_with_alarms(self):
        alarms = [make_alarm(id="a1", label="Test Alarm", hour=7, minute=30)]
        with patch("alarm_clock.cli.load_alarms", return_value=alarms):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "Test Alarm" in result.stdout


class TestCLIAdd:
    def test_add_alarm(self):
        with patch("alarm_clock.cli.load_alarms", return_value=[]):
            with patch("alarm_clock.cli.save_alarms"):
                result = runner.invoke(app, ["add", "07:30", "--label", "Wake up"])
                assert result.exit_code == 0
                assert "Wake up" in result.stdout

    def test_add_with_repeat(self):
        with patch("alarm_clock.cli.load_alarms", return_value=[]):
            with patch("alarm_clock.cli.save_alarms"):
                result = runner.invoke(app, ["add", "09:00", "--label", "Standup", "--repeat"])
                assert result.exit_code == 0
                assert "Standup" in result.stdout

    def test_add_invalid_time(self):
        result = runner.invoke(app, ["add", "25:00"])
        assert result.exit_code == 1


class TestCLIDelete:
    def test_delete_by_number(self):
        alarms = [make_alarm(id="a1", label="To Delete")]
        with patch("alarm_clock.cli.load_alarms", return_value=alarms):
            with patch("alarm_clock.cli.save_alarms"):
                result = runner.invoke(app, ["delete", "1"])
                assert result.exit_code == 0
                assert "Deleted" in result.stdout

    def test_delete_not_found(self):
        with patch("alarm_clock.cli.load_alarms", return_value=[]):
            result = runner.invoke(app, ["delete", "1"])
            assert result.exit_code == 1


class TestCLIEnable:
    def test_enable_alarm(self):
        alarms = [make_alarm(id="a1", active=False)]
        with patch("alarm_clock.cli.load_alarms", return_value=alarms):
            with patch("alarm_clock.cli.save_alarms"):
                result = runner.invoke(app, ["enable", "1"])
                assert result.exit_code == 0

    def test_enable_not_found(self):
        with patch("alarm_clock.cli.load_alarms", return_value=[]):
            result = runner.invoke(app, ["enable", "1"])
            assert result.exit_code == 1


class TestCLIHelp:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 2
        assert "Usage" in result.stdout
