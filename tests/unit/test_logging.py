"""Tests for alarm_clock.logging_conf."""

from alarm_clock.config import Config, LoggingConfig
from alarm_clock.logging_conf import setup_logging, get_logger


class TestSetupLogging:
    def test_setup_default(self):
        config = Config()
        setup_logging(config)

    def test_setup_json_format(self):
        config = Config(logging=LoggingConfig(level="DEBUG", json_format=True,
                        file="/tmp/test-alarm-clock.log"))
        setup_logging(config)

    def test_setup_custom_path(self, tmp_path):
        log_file = tmp_path / "test.log"
        config = Config(logging=LoggingConfig(level="INFO", file=str(log_file)))
        setup_logging(config)

    def test_get_logger(self):
        logger = get_logger("test_module")
        assert logger is not None
