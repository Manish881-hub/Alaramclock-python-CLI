"""alarm_clock - Production-ready terminal alarm clock."""

from importlib.metadata import version

try:
    __version__ = version("alarm-clock")
except Exception:
    __version__ = "0.0.0"

__all__ = ["__version__"]
