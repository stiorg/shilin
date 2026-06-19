"""Drawing routines for menus and quiz screens."""

from __future__ import annotations

import os

import pygame

from game import config

COLOR_BG = (24, 28, 42)
COLOR_HUD = (18, 22, 34)
COLOR_TEXT = (230, 235, 245)
COLOR_MUTED = (140, 150, 170)
COLOR_SELECT = (255, 210, 80)
COLOR_SELECT_BG = (55, 65, 95)
COLOR_OPTION = (36, 42, 62)
COLOR_CORRECT = (80, 200, 120)
COLOR_WRONG = (220, 90, 90)
COLOR_CHAR = (255, 245, 220)


def _font_candidates() -> list[str]:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled = os.path.join(root, "fonts", "NotoSansTC-Regular.otf")
    return [
        bundled,
        "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/msjhbd.ttc",
        "C:/Windows/Fonts/NotoSansTC-Regular.otf",
    ]


def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
    for path in _font_candidates():
        if os.path.isfile(path):
            try:
                return pygame.font.Font(path, size)
            except (OSError, pygame.error):
                continue
    if config.is_handheld():
        return pygame.font.Font(None, size + (6 if bold else 0))
    for name in ("microsoft jhenghei", "noto sans tc", "arial unicode ms", "consolas"):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except (OSError, pygame.error):
            continue
    return pygame.font.Font(None, size + (6 if bold else 0))


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = _load_font(config.FONT_NORMAL)
        self.font_large = _load_font(config.FONT_LARGE, bold=True)
        self.font_small = _load_font(config.FONT_SMALL)
        self.font_char = _load_font(config.FONT_CHAR, bold=True)

    def clear(self) -> None:
        self.screen.fill(COLOR_BG)

    def _handheld_hint(self, quiz: bool = False) -> str:
        if quiz:
            if config.is_handheld():
                return "D-pad — Move | A — Confirm | B — Back | Start+Select — Exit"
            return "1-5 — Answer | D-pad+Enter — Select | Esc — Back"
        if config.is_handheld():
            return "Start+Select — Exit | B — Back"
        return "Esc — Back | Enter — Select"

    def draw_menu(self, title: str, items: list[str], selected: int, subtitle: str, extra: str = "") -> None:
        self.clear()
        pygame.draw.rect(self.screen, COLOR_HUD, (0, 0, config.SCREEN_WIDTH, config.HUD_HEIGHT))

        title_surf = self.font_large.render(title, True, COLOR_TEXT)
        self.screen.blit(title_surf, (config.SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 28))

        sub = self.font_small.render(subtitle, True, COLOR_MUTED)
        self.screen.blit(sub, (config.SCREEN_WIDTH // 2 - sub.get_width() // 2, 88))

        if extra:
            extra_surf = self.font.render(extra, True, COLOR_SELECT)
            self.screen.blit(extra_surf, (config.SCREEN_WIDTH // 2 - extra_surf.get_width() // 2, 118))

        start_y = 160 if extra else 140
        for i, label in enumerate(items):
            y = start_y + i * (config.OPTION_HEIGHT + config.OPTION_GAP)
            rect = pygame.Rect(80, y, config.SCREEN_WIDTH - 160, config.OPTION_HEIGHT)
            selected_row = i == selected
            bg = COLOR_SELECT_BG if selected_row else COLOR_OPTION
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            if selected_row:
                pygame.draw.rect(self.screen, COLOR_SELECT, rect, 2, border_radius=8)
            prefix = "> " if selected_row else "  "
            text = self.font.render(prefix + label, True, COLOR_SELECT if selected_row else COLOR_TEXT)
            self.screen.blit(text, (rect.x + 16, rect.centery - text.get_height() // 2))

        hint = self.font_small.render(self._handheld_hint(), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))

    def draw_quiz(
        self,
        mode_label: str,
        status: str,
        char: str,
        level_label: str,
        choices: list[str],
        selected: int,
        feedback: str | None = None,
        feedback_ok: bool | None = None,
    ) -> None:
        self.clear()
        pygame.draw.rect(self.screen, COLOR_HUD, (0, 0, config.SCREEN_WIDTH, config.HUD_HEIGHT))

        left = self.font_small.render(mode_label, True, COLOR_MUTED)
        right = self.font_small.render(status, True, COLOR_SELECT if "Streak" in status else COLOR_TEXT)
        self.screen.blit(left, (12, 12))
        self.screen.blit(right, (config.SCREEN_WIDTH - right.get_width() - 12, 12))

        char_surf = self.font_char.render(char, True, COLOR_CHAR)
        self.screen.blit(char_surf, (config.SCREEN_WIDTH // 2 - char_surf.get_width() // 2, 58))

        level = self.font.render(level_label, True, COLOR_MUTED)
        self.screen.blit(level, (config.SCREEN_WIDTH // 2 - level.get_width() // 2, 178))

        start_y = 210
        for i, choice in enumerate(choices):
            y = start_y + i * (config.OPTION_HEIGHT + config.OPTION_GAP)
            rect = pygame.Rect(60, y, config.SCREEN_WIDTH - 120, config.OPTION_HEIGHT)
            selected_row = i == selected
            bg = COLOR_SELECT_BG if selected_row else COLOR_OPTION
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            if selected_row:
                pygame.draw.rect(self.screen, COLOR_SELECT, rect, 2, border_radius=8)
            if config.is_handheld():
                prefix = "> " if selected_row else "  "
                label = prefix + choice
            else:
                label = f"[{i + 1}] {choice}"
            text = self.font.render(label, True, COLOR_SELECT if selected_row else COLOR_TEXT)
            self.screen.blit(text, (rect.x + 16, rect.centery - text.get_height() // 2))

        if feedback:
            color = COLOR_CORRECT if feedback_ok else COLOR_WRONG
            fb = self.font.render(feedback, True, color)
            self.screen.blit(fb, (config.SCREEN_WIDTH // 2 - fb.get_width() // 2, config.SCREEN_HEIGHT - 56))

        hint = self.font_small.render(self._handheld_hint(quiz=True), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))
