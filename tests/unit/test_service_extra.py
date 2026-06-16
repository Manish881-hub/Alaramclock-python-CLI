"""Additional service tests for uncovered paths."""

from unittest.mock import patch

from alarm_clock.service import (
    install_service,
    uninstall_service,
    run_daemon,
)


class TestServiceDispatch:
    def test_install_unsupported_platform(self):
        with patch("platform.system", return_value="Darwin"):
            with patch("alarm_clock.service.logger") as mock_log:
                result = install_service()
                assert result is False
                mock_log.error.assert_called_once()

    def test_uninstall_unsupported_platform(self):
        with patch("platform.system", return_value="Darwin"):
            with patch("alarm_clock.service.logger") as mock_log:
                result = uninstall_service()
                assert result is False


class TestRunDaemon:
    def test_daemon_keyboard_interrupt(self):
        config = None
        alarms = []
        lock = None
        audio = None
        monitor = MagicMock()
        monitor.is_alive.return_value = True

        with patch("alarm_clock.service.time.sleep", side_effect=KeyboardInterrupt):
            run_daemon(config, alarms, lock, audio, monitor)

        monitor.stop.assert_called_once()

    def test_daemon_normal_exit(self):
        config = None
        alarms = []
        lock = None
        audio = None
        monitor = MagicMock()
        monitor.is_alive.side_effect = [True, False]

        with patch("alarm_clock.service.time.sleep"):
            run_daemon(config, alarms, lock, audio, monitor)

        monitor.stop.assert_called_once()
        monitor.join.assert_called_once_with(timeout=5)


from unittest.mock import MagicMock


class TestWindowsServiceNSSM:
    def test_windows_nssm_success(self):
        with patch("platform.system", return_value="Windows"):
            with patch("alarm_clock.service.get_executable_path", return_value="C:\\alarm-clock.exe"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    mock_path = MagicMock()
                    mock_path.exists.return_value = True
                    with patch("alarm_clock.service.Path", return_value=mock_path):
                        import alarm_clock.service as svc
                        original_find = svc.subprocess.run
                        try:
                            svc.subprocess.run = MagicMock(return_value=MagicMock(returncode=0))
                            # Trigger NSSM path
                            with patch("alarm_clock.service.Path.exists", return_value=True):
                                from alarm_clock.service import install_windows_service
                                with patch("alarm_clock.service.subprocess") as mock_sp:
                                    result = install_windows_service()
                        finally:
                            svc.subprocess.run = original_find


class TestSystemdUserDetection:
    def test_no_user_found(self):
        with patch("platform.system", return_value="Linux"):
            with patch("alarm_clock.service.os.environ.get", return_value=None):
                with patch("alarm_clock.service.logger") as mock_log:
                    from alarm_clock.service import install_systemd_service
                    result = install_systemd_service()
                    assert result is False
