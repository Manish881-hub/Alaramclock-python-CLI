"""Configuration management using TOML."""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class GeneralConfig:
    snooze_minutes: int = 5
    auto_dismiss_seconds: int = 30
    poll_interval_seconds: int = 1
    ring_repeat_seconds: int = 5
    timezone: str = "local"


@dataclass
class AudioConfig:
    enabled: bool = True
    volume: float = 1.0
    custom_sound: str = ""


@dataclass
class StorageConfig:
    path: str = "~/.local/share/alarm-clock/alarms.json"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "~/.local/share/alarm-clock/alarm-clock.log"
    max_size_mb: int = 5
    backup_count: int = 3
    json_format: bool = False


@dataclass
class TUIConfig:
    enabled: bool = False
    theme: str = "dark"


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tui: TUIConfig = field(default_factory=TUIConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Config":
        if config_path is None:
            config_path = cls._default_config_path()

        if not config_path.exists():
            return cls()

        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            return cls()

        return cls(
            general=GeneralConfig(**data.get("general", {})),
            audio=AudioConfig(**data.get("audio", {})),
            storage=StorageConfig(**data.get("storage", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            tui=TUIConfig(**data.get("tui", {})),
        )

    def save(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = self._default_config_path()

        config_path.parent.mkdir(parents=True, exist_ok=True)

        import tomli_w

        with config_path.open("wb") as f:
            tomli_w.dump(
                {
                    "general": self.general.__dict__,
                    "audio": self.audio.__dict__,
                    "storage": self.storage.__dict__,
                    "logging": self.logging.__dict__,
                    "tui": self.tui.__dict__,
                },
                f,
            )

    @staticmethod
    def _default_config_path() -> Path:
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "alarm-clock" / "config.toml"

    @staticmethod
    def _default_data_dir() -> Path:
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / "alarm-clock"

    def get_storage_path(self) -> Path:
        return Path(self.storage.path).expanduser()

    def get_log_path(self) -> Path:
        return Path(self.logging.file).expanduser()
