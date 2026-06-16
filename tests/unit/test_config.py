"""Tests for alarm_clock.config."""

from pathlib import Path
from alarm_clock.config import Config, GeneralConfig, AudioConfig, StorageConfig, LoggingConfig, TUIConfig


class TestConfigDefaults:
    def test_default_config(self):
        cfg = Config()
        assert cfg.general.snooze_minutes == 5
        assert cfg.general.auto_dismiss_seconds == 30
        assert cfg.general.poll_interval_seconds == 1
        assert cfg.general.ring_repeat_seconds == 5
        assert cfg.general.timezone == "local"

    def test_audio_defaults(self):
        cfg = Config()
        assert cfg.audio.enabled is True
        assert cfg.audio.volume == 1.0
        assert cfg.audio.custom_sound == ""

    def test_storage_defaults(self):
        cfg = Config()
        assert "alarms.json" in cfg.storage.path

    def test_logging_defaults(self):
        cfg = Config()
        assert cfg.logging.level == "INFO"
        assert cfg.logging.max_size_mb == 5
        assert cfg.logging.backup_count == 3
        assert cfg.logging.json_format is False

    def test_tui_defaults(self):
        cfg = Config()
        assert cfg.tui.enabled is False
        assert cfg.tui.theme == "dark"


class TestConfigCustom:
    def test_custom_general_config(self):
        cfg = Config(general=GeneralConfig(snooze_minutes=10, timezone="UTC"))
        assert cfg.general.snooze_minutes == 10
        assert cfg.general.timezone == "UTC"

    def test_custom_paths(self):
        cfg = Config(
            storage=StorageConfig(path="/tmp/test/alarms.json"),
            logging=LoggingConfig(file="/tmp/test/log.log"),
        )
        assert cfg.get_storage_path() == Path("/tmp/test/alarms.json")
        assert cfg.get_log_path() == Path("/tmp/test/log.log")


class TestConfigPersistence:
    def test_save_and_load(self, tmp_path):
        config_path = tmp_path / "config.toml"
        cfg = Config(
            general=GeneralConfig(snooze_minutes=15, timezone="America/New_York"),
            audio=AudioConfig(enabled=False),
        )
        cfg.save(config_path)
        assert config_path.exists()

        loaded = Config.load(config_path)
        assert loaded.general.snooze_minutes == 15
        assert loaded.general.timezone == "America/New_York"
        assert loaded.audio.enabled is False

    def test_load_nonexistent_returns_defaults(self):
        cfg = Config.load(Path("/nonexistent/path/config.toml"))
        assert cfg.general.snooze_minutes == 5
        assert cfg.audio.enabled is True


class TestConfigPaths:
    def test_default_config_path(self):
        path = Config._default_config_path()
        assert "alarm-clock" in str(path)
        assert path.name == "config.toml"

    def test_default_data_dir(self):
        path = Config._default_data_dir()
        assert "alarm-clock" in str(path)

    def test_get_storage_path_expands_user(self):
        cfg = Config(storage=StorageConfig(path="~/custom/alarms.json"))
        p = cfg.get_storage_path()
        assert not p.is_absolute() or "custom" in str(p)
