#!/usr/bin/env python3
"""Bopomofo Training — PC and Anbernic RG34XXSP (muOS) compatible."""

from __future__ import annotations

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LIBS = os.path.join(ROOT, "libs")

_LOG_PATHS = (
    os.path.join(ROOT, "log.txt"),
    "/mnt/mmc/ports/bopomofo/log.txt",
    "/mnt/sdcard/ports/bopomofo/log.txt",
    "/mnt/mmc/ROMS/Ports/bopomofo.log",
    "/tmp/bopomofo.log",
)


def _log(msg: str) -> None:
    line = f"[bopomofo] {msg}\n"
    for path in _LOG_PATHS:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
            break
        except OSError:
            continue
    if os.environ.get("BOPOMOFO_DEBUG"):
        print(line, end="")


def _setup_pygame_path() -> None:
    if os.environ.get("MUOS") == "1":
        return
    if os.path.isdir(LIBS) and LIBS not in sys.path:
        sys.path.insert(0, LIBS)


def _scrub_libs_from_path() -> None:
    if os.environ.get("MUOS") != "1":
        return
    norm_libs = os.path.normpath(LIBS)
    sys.path[:] = [p for p in sys.path if os.path.normpath(p) != norm_libs]


def _import_pygame():
    _scrub_libs_from_path()
    _setup_pygame_path()
    try:
        import pygame as pg

        _log(f"pygame loaded: {pg.__file__}")
        if os.environ.get("MUOS") == "1" and "/libs/" in pg.__file__:
            _log("WARN: bundled pygame cannot use handheld screen. SSH: pip3 install --user pygame")
        return pg
    except ImportError:
        pass
    if os.path.isdir(LIBS) and LIBS not in sys.path:
        sys.path.insert(0, LIBS)
    import pygame as pg

    _log(f"pygame loaded from libs: {pg.__file__}")
    return pg


def _setup_sdl_env() -> None:
    if sys.platform != "linux":
        return
    os.environ.setdefault("SDL_AUDIODRIVER", "alsa")


_log("boot")
_setup_sdl_env()
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    _log("import pygame...")
    pygame = _import_pygame()

    _log("import game...")
    from game import config
    from game.app import App
except Exception:
    _log("import failed:\n" + traceback.format_exc())
    raise

_BAD_DRIVERS = frozenset({"dummy", "offscreen", ""})


def _display_drivers() -> list[str | None]:
    if os.environ.get("MUOS") == "1":
        preferred = ("kmsdrm", None, "fbcon", "mali")
    else:
        preferred = (None, "fbcon", "x11")

    order: list[str | None] = []
    for drv in preferred:
        if drv not in order:
            order.append(drv)
    return order


def _apply_driver_env(drv: str | None) -> None:
    if drv:
        os.environ["SDL_VIDEODRIVER"] = drv
        if drv == "fbcon":
            for fb in ("/dev/fb0", "/dev/fb1"):
                if os.path.exists(fb):
                    os.environ["SDL_FBDEV"] = fb
                    break
    else:
        os.environ.pop("SDL_VIDEODRIVER", None)


def _reset_pygame() -> None:
    if pygame.get_init():
        try:
            pygame.display.quit()
        except pygame.error:
            pass
        pygame.quit()


def _validate_screen(screen: pygame.Surface, drv_label: str) -> None:
    name = pygame.display.get_driver()
    _log(f"SDL video driver: {name!r} (try={drv_label})")
    if name in _BAD_DRIVERS:
        raise pygame.error(f"unusable video driver: {name!r}")
    screen.fill((24, 28, 42))
    pygame.display.flip()
    _log("splash flip ok")


def init_pygame() -> pygame.Surface:
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    _log(
        f"SDL env: VIDEODRIVER={os.environ.get('SDL_VIDEODRIVER', 'auto')} "
        f"LD_PRELOAD={os.environ.get('LD_PRELOAD', 'unset')} "
        f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH', 'unset')[:120]}"
    )
    width, height = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
    fullscreen = config.default_fullscreen()
    flags = pygame.FULLSCREEN if fullscreen else 0
    last_error: pygame.error | None = None

    for drv in _display_drivers():
        _apply_driver_env(drv)
        drv_label = drv or "auto"
        _log(f"try driver={drv_label} fullscreen={fullscreen}")
        _reset_pygame()
        try:
            pygame.init()
            pygame.joystick.init()
            pygame.display.set_caption("Bopomofo Training")
            try:
                screen = pygame.display.set_mode((width, height), flags)
            except pygame.error:
                if not flags:
                    raise
                _log("fullscreen failed, trying windowed on same driver")
                screen = pygame.display.set_mode((width, height))
            _validate_screen(screen, drv_label)
            _log(f"display ready size={screen.get_size()}")
            return screen
        except pygame.error as exc:
            last_error = exc
            _log(f"driver {drv_label} failed: {exc}")

    raise last_error or pygame.error("no display driver available")


def main() -> None:
    _log("main start")
    screen = init_pygame()
    App(screen).run()
    pygame.quit()
    _log("exit ok")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log("fatal:\n" + traceback.format_exc())
        sys.exit(1)
