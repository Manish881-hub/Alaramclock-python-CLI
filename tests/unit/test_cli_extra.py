"""Additional CLI tests for uncovered paths."""

from unittest.mock import patch
from typer.testing import CliRunner

from alarm_clock.cli import app
from alarm_clock.models import Alarm

runner = CliRunner()


def make_alarm(**kwargs) -> Alarm:
    defaults = dict(id="test-id", label="Test", hour=8, minute=0,
                    repeat_daily=False, active=True, snoozed_until=None)
    return Alarm(**{**defaults, **kwargs})


class TestCLIDaemon:
    def test_daemon_command(self):
        with patch("alarm_clock.cli.load_alarms", return_value=[]):
            with patch("alarm_clock.cli.run_daemon"):
                result = runner.invoke(app, ["daemon"])
                assert result.exit_code == 0


class TestCLIInstall:
    def test_install_success(self):
        with patch("alarm_clock.cli.install_service", return_value=True):
            result = runner.invoke(app, ["install"])
            assert result.exit_code == 0
            assert "successfully" in result.stdout

    def test_install_failure(self):
        with patch("alarm_clock.cli.install_service", return_value=False):
            result = runner.invoke(app, ["install"])
            assert result.exit_code == 1


class TestCLIUninstall:
    def test_uninstall_success(self):
        with patch("alarm_clock.cli.uninstall_service", return_value=True):
            result = runner.invoke(app, ["uninstall"])
            assert result.exit_code == 0
            assert "successfully" in result.stdout

    def test_uninstall_failure(self):
        with patch("alarm_clock.cli.uninstall_service", return_value=False):
            result = runner.invoke(app, ["uninstall"])
            assert result.exit_code == 1


class TestCLIDisplay:
    def test_list_rich_table(self):
        alarms = [
            make_alarm(id="a1", label="Alpha", hour=7, minute=0, repeat_daily=True),
            make_alarm(id="a2", label="Beta", hour=9, minute=30, repeat_daily=False, active=False),
        ]
        with patch("alarm_clock.cli.load_alarms", return_value=alarms):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "Alpha" in result.stdout
            assert "Beta" in result.stdout


class TestCLIDeleteByID:
    def test_delete_by_id_prefix(self):
        alarms = [make_alarm(id="abc123def", label="ByID")]
        with patch("alarm_clock.cli.load_alarms", return_value=alarms):
            with patch("alarm_clock.cli.save_alarms"):
                result = runner.invoke(app, ["delete", "abc"])
                assert result.exit_code == 0
                assert "Deleted" in result.stdout

    def test_delete_nonexistent_id(self):
        alarms = [make_alarm(id="abc")]
        with patch("alarm_clock.cli.load_alarms", return_value=alarms):
            result = runner.invoke(app, ["delete", "xyz"])
            assert result.exit_code == 1
