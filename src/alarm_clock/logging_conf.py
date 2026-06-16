"""Logging configuration using loguru."""

import sys

from loguru import logger

from alarm_clock.config import Config, LoggingConfig


def setup_logging(config: Config) -> None:
    """Configure loguru with rotation and formatting."""
    logger.remove()

    log_cfg: LoggingConfig = config.logging
    log_path = config.get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = log_cfg.level.upper()

    if log_cfg.json_format:
        fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
        logger.add(
            log_path,
            level=level,
            format=fmt,
            rotation=f"{log_cfg.max_size_mb} MB",
            retention=log_cfg.backup_count,
            compression="gz",
            serialize=True,
        )
    else:
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        logger.add(
            log_path,
            level=level,
            format=fmt,
            rotation=f"{log_cfg.max_size_mb} MB",
            retention=log_cfg.backup_count,
            compression="gz",
        )

    # Console handler for warnings and above
    logger.add(
        sys.stderr,
        level="WARNING",
        format=fmt,
        colorize=True,
    )


def get_logger(name: str | None = None):
    return logger.bind(name=name or "alarm_clock")
