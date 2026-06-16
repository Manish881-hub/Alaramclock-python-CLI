"""Tests for alarm_clock.__init__."""


class TestVersion:
    def test_version_import(self):
        from alarm_clock import __version__
        assert isinstance(__version__, str)
        assert len(__version__) > 0
