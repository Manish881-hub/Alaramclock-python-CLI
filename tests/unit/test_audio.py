"""Tests for alarm_clock.audio."""

from unittest.mock import patch, MagicMock

from alarm_clock.audio import AudioPlayer
from alarm_clock.config import Config, AudioConfig


class TestAudioPlayer:
    def test_disabled_does_nothing(self):
        config = Config(audio=AudioConfig(enabled=False))
        player = AudioPlayer(config)
        with patch("alarm_clock.audio.logger") as mock_log:
            player.play()
            mock_log.debug.assert_called_once()

    def test_windows_beep(self):
        config = Config(audio=AudioConfig(enabled=True))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Windows"):
            with patch("alarm_clock.compat_winsound.Beep") as mock_beep:
                with patch("alarm_clock.audio.time.sleep"):
                    player.play(repeat=1)
                    mock_beep.assert_called_once_with(880, 400)

    def test_fallback_beep(self):
        config = Config(audio=AudioConfig(enabled=True))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Unknown"):
            with patch("sys.stdout") as mock_stdout:
                player.play(repeat=1)
                mock_stdout.write.assert_called_with("\a")

    def test_custom_sound_path_not_found_falls_back(self, tmp_path):
        config = Config(audio=AudioConfig(enabled=True, custom_sound=str(tmp_path / "nonexistent.wav")))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Windows"):
            with patch("alarm_clock.compat_winsound.Beep") as mock_beep:
                with patch("alarm_clock.audio.time.sleep"):
                    player.play(repeat=1)
                    mock_beep.assert_called_once_with(880, 400)

    def test_macos_afplay(self):
        config = Config(audio=AudioConfig(enabled=True))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run") as mock_run:
                player.play(repeat=1)
                mock_run.assert_called_once()

    def test_linux_paplay(self):
        config = Config(audio=AudioConfig(enabled=True))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run", side_effect=[
                MagicMock(returncode=0),
                MagicMock(),
            ]):
                with patch("alarm_clock.audio.time.sleep"):
                    player.play(repeat=1)

    def test_linux_fallback_to_bell(self):
        config = Config(audio=AudioConfig(enabled=True))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run", return_value=MagicMock(returncode=1)):
                with patch("sys.stdout") as mock_stdout:
                    player.play(repeat=1)
                    mock_stdout.write.assert_called_with("\a")
