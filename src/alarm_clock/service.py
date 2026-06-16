"""System service installation (systemd / Windows)."""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from alarm_clock.logging_conf import get_logger

logger = get_logger(__name__)


SYSTEMD_SERVICE = """[Unit]
Description=Alarm Clock Daemon
After=network.target sound.target

[Service]
Type=simple
User={user}
ExecStart={exec_path} daemon
Restart=on-failure
RestartSec=5
Environment=HOME={home}

[Install]
WantedBy=multi-user.target
"""

WINDOWS_SERVICE_PS1 = """$ErrorActionPreference = "Stop"

$serviceName = "AlarmClock"
$displayName = "Alarm Clock Service"
$description = "Background alarm clock daemon"
$exePath = "{exe_path}"
$args = "daemon"

# Check if service exists
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {{
    Write-Host "Service already exists. Removing..."
    sc.exe stop $serviceName
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}}

# Create service
New-Service -Name $serviceName -BinaryPathName "`"$exePath`" $args" `
    -DisplayName $displayName -Description $description `
    -StartupType Automatic

Write-Host "Service created. Starting..."
Start-Service -Name $serviceName
Write-Host "Service started."
"""


def get_executable_path() -> str:
    """Get the path to the alarm-clock executable."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.executable + " -m alarm_clock"


def install_systemd_service() -> bool:
    """Install systemd service (Linux)."""
    if platform.system() != "Linux":
        logger.error("systemd only available on Linux")
        return False

    user = os.environ.get("SUDO_USER") or os.environ.get("USER")
    if not user:
        logger.error("Cannot determine user for systemd service")
        return False

    home = Path.home()
    exec_path = get_executable_path()

    service_content = SYSTEMD_SERVICE.format(
        user=user,
        exec_path=exec_path,
        home=home,
    )

    service_path = Path("/etc/systemd/system/alarm-clock.service")
    try:
        service_path.write_text(service_content)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "alarm-clock"], check=True)
        logger.info("systemd service installed at {}", service_path)
        return True
    except Exception as e:
        logger.error("Failed to install systemd service: {}", e)
        return False


def uninstall_systemd_service() -> bool:
    """Uninstall systemd service."""
    if platform.system() != "Linux":
        return False

    try:
        subprocess.run(["systemctl", "stop", "alarm-clock"], check=False)
        subprocess.run(["systemctl", "disable", "alarm-clock"], check=False)
        Path("/etc/systemd/system/alarm-clock.service").unlink(missing_ok=True)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        logger.info("systemd service uninstalled")
        return True
    except Exception as e:
        logger.error("Failed to uninstall systemd service: {}", e)
        return False


def install_windows_service() -> bool:
    """Install Windows service using NSSM or sc.exe."""
    if platform.system() != "Windows":
        logger.error("Windows service only available on Windows")
        return False

    exe_path = get_executable_path().replace("/", "\\\\")

    try:
        # Try NSSM first (better service management)
        nssm_path = Path("nssm.exe")
        if (
            nssm_path.exists()
            or subprocess.run(["where", "nssm"], capture_output=True).returncode == 0
        ):
            subprocess.run(["nssm", "install", "AlarmClock", exe_path, "daemon"], check=True)
            subprocess.run(["nssm", "set", "AlarmClock", "DisplayName", "Alarm Clock"], check=True)
            subprocess.run(
                ["nssm", "set", "AlarmClock", "Description", "Background alarm clock daemon"],
                check=True,
            )
            subprocess.run(["nssm", "set", "AlarmClock", "Start", "SERVICE_AUTO_START"], check=True)
            subprocess.run(["sc", "start", "AlarmClock"], check=True)
            logger.info("Windows service installed via NSSM")
            return True
    except Exception:
        pass

    # Fallback to sc.exe
    try:
        ps1_content = WINDOWS_SERVICE_PS1.format(exe_path=exe_path)
        result = subprocess.run(
            ["powershell", "-Command", ps1_content], capture_output=True, text=True, check=True
        )
        logger.info("Windows service installed via sc.exe: {}", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to install Windows service: {}", e.stderr)
        return False


def uninstall_windows_service() -> bool:
    """Uninstall Windows service."""
    if platform.system() != "Windows":
        return False

    try:
        subprocess.run(["sc", "stop", "AlarmClock"], check=False)
        subprocess.run(["sc", "delete", "AlarmClock"], check=False)
        logger.info("Windows service uninstalled")
        return True
    except Exception as e:
        logger.error("Failed to uninstall Windows service: {}", e)
        return False


def install_service() -> bool:
    """Install appropriate service for current platform."""
    system = platform.system()
    if system == "Linux":
        return install_systemd_service()
    elif system == "Windows":
        return install_windows_service()
    else:
        logger.error("Service installation not supported on {}", system)
        return False


def uninstall_service() -> bool:
    """Uninstall appropriate service for current platform."""
    system = platform.system()
    if system == "Linux":
        return uninstall_systemd_service()
    elif system == "Windows":
        return uninstall_windows_service()
    else:
        logger.error("Service uninstallation not supported on {}", system)
        return False


def run_daemon(config, alarms, lock, audio_player, monitor) -> None:
    """Run as daemon - blocks until shutdown."""
    import signal

    def signal_handler(signum, frame):
        logger.info("Received signal {}, stopping...", signum)
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Daemon started")
    monitor.start()

    try:
        while monitor.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()
        monitor.join(timeout=5)
        logger.info("Daemon stopped")
