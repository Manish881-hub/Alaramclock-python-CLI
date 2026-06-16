"""Cross-platform audio alert abstraction."""

import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

import alarm_clock.compat_winsound as winsound
from alarm_clock.config import AudioConfig, Config
from alarm_clock.logging_conf import get_logger

logger = get_logger(__name__)


class AudioPlayer:
    """Plays alarm sounds with cross-platform support."""

    def __init__(self, config: Config):
        self.config = config
        self.audio_cfg: AudioConfig = config.audio
        self._lock = threading.Lock()
        self._custom_sound_path: Path | None = None
        if self.audio_cfg.custom_sound:
            self._custom_sound_path = Path(self.audio_cfg.custom_sound).expanduser()

    def play(self, repeat: int = 3, interval: float = 0.15) -> None:
        """Play the alarm sound."""
        if not self.audio_cfg.enabled:
            logger.debug("Audio disabled, skipping beep")
            return

        if self._custom_sound_path and self._custom_sound_path.exists():
            self._play_custom(self._custom_sound_path, repeat, interval)
            return

        system = platform.system()
        try:
            if system == "Darwin":
                self._play_macos(repeat, interval)
            elif system == "Linux":
                self._play_linux(repeat, interval)
            elif system == "Windows":
                self._play_windows(repeat, interval)
            else:
                self._fallback_beep(repeat, interval)
        except Exception as e:
            logger.warning("Audio playback failed: {}", e)
            self._fallback_beep(repeat, interval)

    def _play_macos(self, repeat: int, interval: float) -> None:
        for _ in range(repeat):
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Ping.aiff"],
                check=False,
                timeout=5,
                capture_output=True,
            )
            time.sleep(interval)

    def _play_linux(self, repeat: int, interval: float) -> None:
        for cmd in [
            ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
            ["aplay", "-q", "/usr/share/sounds/alsa/Front_Center.wav"],
        ]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                for _ in range(repeat):
                    subprocess.run(cmd, timeout=5, capture_output=True, check=False)
                    time.sleep(interval)
                return
        self._fallback_beep(repeat, interval)

    def _play_windows(self, repeat: int, interval: float) -> None:
        try:
            for _ in range(repeat):
                winsound.Beep(880, 400)
                time.sleep(interval)
        except Exception:
            self._fallback_beep(repeat, interval)

    def _play_custom(self, path: Path, repeat: int, interval: float) -> None:
        system = platform.system()
        try:
            if system == "Darwin":
                cmd = ["afplay", str(path)]
            elif system == "Linux":
                if subprocess.run(["which", "paplay"], capture_output=True).returncode == 0:
                    cmd = ["paplay", str(path)]
                else:
                    cmd = ["aplay", "-q", str(path)]
            elif system == "Windows":
                for _ in range(repeat):
                    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                    time.sleep(interval)
                return
            else:
                self._fallback_beep(repeat, interval)
                return

            for _ in range(repeat):
                subprocess.run(cmd, timeout=10, capture_output=True, check=False)
                time.sleep(interval)
        except Exception as e:
            logger.warning("Custom sound playback failed: {}", e)
            self._fallback_beep(repeat, interval)

    def _fallback_beep(self, repeat: int, interval: float) -> None:
        """Terminal bell fallback."""
        for _ in range(repeat):
            sys.stdout.write("\a")
            sys.stdout.flush()
            time.sleep(interval)
