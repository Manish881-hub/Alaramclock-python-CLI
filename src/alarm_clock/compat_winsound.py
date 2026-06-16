"""Compatibility wrapper for winsound on non-Windows platforms."""

import sys

if sys.platform == "win32":
    import winsound as _winsound

    Beep = _winsound.Beep
    PlaySound = _winsound.PlaySound
    SND_FILENAME = _winsound.SND_FILENAME
    SND_ASYNC = _winsound.SND_ASYNC
else:

    class _Fallback:
        @staticmethod
        def Beep(frequency: int, duration: int) -> None:
            pass

        @staticmethod
        def PlaySound(*args, **kwargs) -> None:
            pass

    SND_FILENAME = 0
    SND_ASYNC = 1
    Beep = _Fallback.Beep
    PlaySound = _Fallback.PlaySound
