"""Additional audio tests for uncovered paths."""

from unittest.mock import patch, MagicMock

from alarm_clock.audio import AudioPlayer
from alarm_clock.config import Config, AudioConfig


class TestAudioCustomSound:
    def test_custom_sound_macos(self, tmp_path):
        sound = tmp_path / "custom.wav"
        sound.write_text("dummy")
        config = Config(audio=AudioConfig(enabled=True, custom_sound=str(sound)))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run") as mock_run:
                player.play(repeat=1)
                mock_run.assert_called()

    def test_custom_sound_linux_paplay(self, tmp_path):
        sound = tmp_path / "custom.oga"
        sound.write_text("dummy")
        config = Config(audio=AudioConfig(enabled=True, custom_sound=str(sound)))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run", side_effect=[
                MagicMock(returncode=0),
                MagicMock(),
            ]):
                with patch("alarm_clock.audio.time.sleep"):
                    player.play(repeat=1)

    def test_custom_sound_linux_aplay(self, tmp_path):
        sound = tmp_path / "custom.wav"
        sound.write_text("dummy")
        config = Config(audio=AudioConfig(enabled=True, custom_sound=str(sound)))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run", side_effect=[
                MagicMock(returncode=1),
                MagicMock(),
            ]):
                with patch("alarm_clock.audio.time.sleep"):
                    player.play(repeat=1)

    def test_custom_sound_linux_paplay_fallback_to_aplay(self, tmp_path):
        sound = tmp_path / "custom.wav"
        sound.write_text("dummy")
        config = Config(audio=AudioConfig(enabled=True, custom_sound=str(sound)))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Linux"):
            def mock_runs(args, *a, **kw):
                m = MagicMock()
                if "which" in str(args) and "paplay" in str(args):
                    m.returncode = 1
                elif "which" in str(args) and "aplay" in str(args):
                    m.returncode = 0
                else:
                    m.returncode = 0
                return m
            with patch("subprocess.run", side_effect=mock_runs):
                with patch("alarm_clock.audio.time.sleep"):
                    player.play(repeat=1)

    def test_audio_exception_falls_back(self, tmp_path):
        config = Config(audio=AudioConfig(enabled=True))
        player = AudioPlayer(config)
        with patch("platform.system", return_value="Windows"):
            with patch("alarm_clock.audio.winsound.Beep", side_effect=Exception("fail")):
                with patch("sys.stdout") as mock_stdout:
                    player.play(repeat=1)
                    mock_stdout.write.assert_called_with("\a")
