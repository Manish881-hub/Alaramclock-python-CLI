"""Tests for alarm_clock.service."""

from unittest.mock import patch, MagicMock

from alarm_clock.service import (
    get_executable_path,
    install_systemd_service,
    uninstall_systemd_service,
    install_windows_service,
    uninstall_windows_service,
    install_service,
    uninstall_service,
)


class TestGetExecutablePath:
    def test_normal_python(self):
        with patch("alarm_clock.service.sys.frozen", False, create=True):
            path = get_executable_path()
            assert "python" in path
            assert "-m alarm_clock" in path

    def test_frozen(self):
        with patch("alarm_clock.service.sys.frozen", True, create=True):
            with patch("alarm_clock.service.sys.executable", "/usr/bin/alarm-clock"):
                path = get_executable_path()
                assert path == "/usr/bin/alarm-clock"


class TestInstallSystemdService:
    def test_non_linux_returns_false(self):
        with patch("platform.system", return_value="Windows"):
            assert install_systemd_service() is False

    def test_linux_success(self):
        with patch("platform.system", return_value="Linux"):
            with patch("alarm_clock.service.os.environ.get", return_value="testuser"):
                with patch("alarm_clock.service.Path.home", return_value="/home/testuser"):
                    with patch("alarm_clock.service.Path.write_text"):
                        with patch("alarm_clock.service.subprocess.run") as mock_run:
                            mock_run.return_value = MagicMock()
                            assert install_systemd_service() is True

    def test_linux_install_failure(self):
        with patch("platform.system", return_value="Linux"):
            with patch("alarm_clock.service.os.environ.get", return_value="testuser"):
                with patch("alarm_clock.service.Path.home", return_value="/home/testuser"):
                    with patch("alarm_clock.service.Path.write_text"):
                        with patch("alarm_clock.service.subprocess.run", side_effect=Exception("fail")):
                            assert install_systemd_service() is False


class TestInstallWindowsService:
    def test_non_windows_returns_false(self):
        with patch("platform.system", return_value="Linux"):
            assert install_windows_service() is False

    def test_windows_success(self):
        with patch("platform.system", return_value="Windows"):
            with patch("alarm_clock.service.get_executable_path", return_value="C:\\alarm-clock.exe"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    with patch("alarm_clock.service.Path.exists", return_value=True):
                        assert install_windows_service() is True


class TestUninstallService:
    def test_uninstall_systemd(self):
        with patch("platform.system", return_value="Linux"):
            with patch("alarm_clock.service.subprocess.run") as mock_run:
                with patch("alarm_clock.service.Path.unlink"):
                    assert uninstall_systemd_service() is True

    def test_uninstall_windows(self):
        with patch("platform.system", return_value="Windows"):
            with patch("alarm_clock.service.subprocess.run"):
                assert uninstall_windows_service() is True


class TestInstallServiceDispatcher:
    def test_install_linux(self):
        with patch("alarm_clock.service.install_systemd_service", return_value=True):
            with patch("platform.system", return_value="Linux"):
                assert install_service() is True

    def test_install_windows(self):
        with patch("alarm_clock.service.install_windows_service", return_value=True):
            with patch("platform.system", return_value="Windows"):
                assert install_service() is True

    def test_uninstall_linux(self):
        with patch("alarm_clock.service.uninstall_systemd_service", return_value=True):
            with patch("platform.system", return_value="Linux"):
                assert uninstall_service() is True

    def test_uninstall_windows(self):
        with patch("alarm_clock.service.uninstall_windows_service", return_value=True):
            with patch("platform.system", return_value="Windows"):
                assert uninstall_service() is True
