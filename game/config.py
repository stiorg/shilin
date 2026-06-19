"""Runtime configuration — tuned for RG34XXSP (720x480) and PC."""

import os
import sys

SCREEN_WIDTH = 720
SCREEN_HEIGHT = 480


def is_handheld() -> bool:
    return (
        os.environ.get("DEVICE", "").upper() in ("RG34XXSP", "RG34XX", "RG35XX")
        or os.environ.get("MUOS", "") == "1"
        or os.path.exists("/opt/muos")
        or (sys.platform == "linux" and os.environ.get("DISPLAY", "") == "")
    )


_handheld = is_handheld()
HUD_HEIGHT = 44 if _handheld else 36
FONT_NORMAL = 24 if _handheld else 18
FONT_LARGE = 72 if _handheld else 56
FONT_SMALL = 18 if _handheld else 14
FONT_CHAR = 120 if _handheld else 96

OPTION_HEIGHT = 52 if _handheld else 40
OPTION_GAP = 6
FEEDBACK_DURATION = 1.8

FPS = 60


def default_fullscreen() -> bool:
    return os.environ.get("MUOS") == "1" or bool(os.environ.get("DEVICE"))
