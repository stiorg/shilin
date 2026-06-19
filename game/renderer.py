"""Drawing routines for menus and quiz screens."""

from __future__ import annotations

import os

import pygame

from game import config
from game.deck_store import chinese_display
from game.pinyin import build_reading, is_cjk_script_char, needs_cjk_font

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
CHOICE_MAX_LEN = 34


def _truncate(text: str, max_len: int = CHOICE_MAX_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cjk_font_candidates() -> list[str]:
    root = _project_root()
    return [
        os.path.join(root, "fonts", "NotoSansTC-Regular.otf"),
        "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/msjhbd.ttc",
        "C:/Windows/Fonts/NotoSansTC-Regular.otf",
    ]


def _latin_font_candidates() -> list[str]:
    root = _project_root()
    return [
        os.path.join(root, "fonts", "NotoSans-Regular.ttf"),
        os.path.join(root, "fonts", "NotoSans-Regular.otf"),
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]


def _load_from_paths(paths: list[str], size: int) -> pygame.font.Font | None:
    for path in paths:
        if os.path.isfile(path):
            try:
                return pygame.font.Font(path, size)
            except (OSError, pygame.error):
                continue
    return None


def _load_cjk_font(size: int, bold: bool = False) -> pygame.font.Font:
    font = _load_from_paths(_cjk_font_candidates(), size)
    if font is not None:
        return font
    if config.is_handheld():
        return pygame.font.Font(None, size + (6 if bold else 0))
    for name in ("microsoft jhenghei", "noto sans tc", "arial unicode ms"):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except (OSError, pygame.error):
            continue
    return pygame.font.Font(None, size + (6 if bold else 0))


def _load_latin_font(size: int, bold: bool = False) -> pygame.font.Font:
    font = _load_from_paths(_latin_font_candidates(), size)
    if font is not None:
        return font
    if config.is_handheld():
        return pygame.font.Font(None, size + (6 if bold else 0))
    for name in ("segoe ui", "arial", "calibri", "noto sans", "dejavu sans", "consolas"):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except (OSError, pygame.error):
            continue
    return _load_cjk_font(size, bold)


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = _load_latin_font(config.FONT_NORMAL)
        self.font_large = _load_latin_font(config.FONT_LARGE, bold=True)
        self.font_small = _load_latin_font(config.FONT_SMALL)
        self.font_cjk = _load_cjk_font(config.FONT_CHAR, bold=True)
        self.font_cjk_large = _load_cjk_font(config.FONT_LARGE, bold=True)
        self.font_cjk_normal = _load_cjk_font(config.FONT_NORMAL)

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

    def draw_menu(
        self,
        title: str,
        items: list[str],
        selected: int,
        subtitle: str,
        extra: str = "",
        footer_hint: str = "",
    ) -> None:
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
        row_h = config.OPTION_HEIGHT
        if len(items) > 4:
            row_h = max(36, config.OPTION_HEIGHT - 10)
        for i, label in enumerate(items):
            y = start_y + i * (row_h + config.OPTION_GAP)
            rect = pygame.Rect(80, y, config.SCREEN_WIDTH - 160, row_h)
            selected_row = i == selected
            bg = COLOR_SELECT_BG if selected_row else COLOR_OPTION
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            if selected_row:
                pygame.draw.rect(self.screen, COLOR_SELECT, rect, 2, border_radius=8)
            prefix = "> " if selected_row else "  "
            text = self.font.render(prefix + label, True, COLOR_SELECT if selected_row else COLOR_TEXT)
            self.screen.blit(text, (rect.x + 16, rect.centery - text.get_height() // 2))

        hint = self.font_small.render(footer_hint or self._handheld_hint(), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))

    def _tone_hint(self) -> str:
        if config.is_handheld():
            return "↑↓ Tone | ←→ Syllable | A — Check | B — Back"
        return "↑↓ Tone | ←→ Syllable | Enter — Check | Esc — Back"

    def _blit_level_label(self, level_label: str) -> None:
        surf = self.font_small.render(level_label, True, COLOR_MUTED)
        self.screen.blit(surf, (12, 130))

    def draw_tone_quiz(
        self,
        mode_label: str,
        status: str,
        char: str,
        level_label: str,
        syllables: list[str],
        tones: list[int],
        selected_idx: int,
        feedback: str | None = None,
        feedback_ok: bool | None = None,
        correct_reading: str = "",
        your_reading: str = "",
    ) -> None:
        self.clear()
        pygame.draw.rect(self.screen, COLOR_HUD, (0, 0, config.SCREEN_WIDTH, config.HUD_HEIGHT))

        left = self.font_small.render(mode_label, True, COLOR_MUTED)
        right = self.font_small.render(status, True, COLOR_SELECT if "Streak" in status else COLOR_TEXT)
        self.screen.blit(left, (12, 12))
        self.screen.blit(right, (config.SCREEN_WIDTH - right.get_width() - 12, 12))

        _prompt_font, prompt_surf = self._fit_prompt(char)
        self.screen.blit(
            prompt_surf,
            (config.SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, 52),
        )

        self._blit_level_label(level_label)

        show_wrong_panel = feedback_ok is False and correct_reading

        if not show_wrong_panel:
            toned = [build_reading([syl], [tone]) for syl, tone in zip(syllables, tones)]
            gap = 16
            surfaces: list[tuple[pygame.Surface, str]] = []
            for i, text in enumerate(toned):
                color = COLOR_SELECT if i == selected_idx else COLOR_TEXT
                surfaces.append((self._pinyin_font(large=True).render(text, True, color), text))
            total_w = sum(s[0].get_width() for s in surfaces) + gap * max(0, len(surfaces) - 1)
            x = config.SCREEN_WIDTH // 2 - total_w // 2
            y = 228
            row_h = max(s[0].get_height() for s in surfaces) if surfaces else config.FONT_LARGE
            pad_x, pad_y = 14, 8
            for i, (surf, _text) in enumerate(surfaces):
                rect = pygame.Rect(
                    x - pad_x,
                    y - pad_y,
                    surf.get_width() + pad_x * 2,
                    surf.get_height() + pad_y * 2,
                )
                selected = i == selected_idx
                bg = COLOR_SELECT_BG if selected else COLOR_OPTION
                pygame.draw.rect(self.screen, bg, rect, border_radius=8)
                if selected:
                    pygame.draw.rect(self.screen, COLOR_SELECT, rect, 2, border_radius=8)
                self.screen.blit(surf, (x, y))
                x += surf.get_width() + gap

            tone_y = y + row_h + pad_y * 2 + 20
            tone_label = self.font.render(f"Tone {tones[selected_idx]}", True, COLOR_MUTED)
            self.screen.blit(
                tone_label,
                (config.SCREEN_WIDTH // 2 - tone_label.get_width() // 2, tone_y),
            )

        if show_wrong_panel:
            self._draw_tone_wrong_feedback(
                correct_reading, your_reading, feedback or "", 200
            )
        elif feedback:
            color = COLOR_CORRECT if feedback_ok else COLOR_WRONG
            self._blit_feedback(feedback, color, config.SCREEN_HEIGHT - 56)

        hint = self.font_small.render(self._tone_hint(), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))

    def _draw_syllable_row(
        self,
        syllable_texts: list[str],
        y: int,
        color: tuple[int, int, int],
        *,
        highlight: bool = False,
    ) -> int:
        gap = 16
        pad_x, pad_y = 14, 8
        surfaces = [
            self._pinyin_font(large=True).render(text, True, color) for text in syllable_texts
        ]
        total_w = sum(s.get_width() for s in surfaces) + gap * max(0, len(surfaces) - 1)
        x = config.SCREEN_WIDTH // 2 - total_w // 2
        row_h = max(s.get_height() for s in surfaces) if surfaces else config.FONT_LARGE
        for surf in surfaces:
            rect = pygame.Rect(
                x - pad_x,
                y - pad_y,
                surf.get_width() + pad_x * 2,
                surf.get_height() + pad_y * 2,
            )
            bg = COLOR_SELECT_BG if highlight else COLOR_OPTION
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            if highlight:
                pygame.draw.rect(self.screen, color, rect, 2, border_radius=8)
            self.screen.blit(surf, (x, y))
            x += surf.get_width() + gap
        return y + row_h + pad_y * 2

    def _draw_tone_wrong_feedback(
        self, correct_reading: str, your_reading: str, note: str, start_y: int
    ) -> None:
        y = start_y
        label = self.font.render("Wrong", True, COLOR_WRONG)
        self.screen.blit(label, (config.SCREEN_WIDTH // 2 - label.get_width() // 2, y))
        y += label.get_height() + 12

        if your_reading:
            prefix = self.font.render("You entered: ", True, COLOR_MUTED)
            entry = self._pinyin_font().render(your_reading, True, COLOR_WRONG)
            total_w = prefix.get_width() + entry.get_width()
            x = config.SCREEN_WIDTH // 2 - total_w // 2
            self.screen.blit(prefix, (x, y))
            self.screen.blit(entry, (x + prefix.get_width(), y))
            y += max(prefix.get_height(), entry.get_height()) + 16

        answer_label = self.font_small.render("Correct reading", True, COLOR_MUTED)
        self.screen.blit(
            answer_label,
            (config.SCREEN_WIDTH // 2 - answer_label.get_width() // 2, y),
        )
        y += 22

        correct_parts = correct_reading.split()
        y = self._draw_syllable_row(correct_parts, y + 4, COLOR_CORRECT, highlight=True) + 8

        if note:
            y += 26
            self._blit_feedback(note, COLOR_MUTED, y)

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
        prompt_hint: str = "",
        chinese_choices: bool = False,
        prompt_style: str = "chinese",
    ) -> None:
        self.clear()
        pygame.draw.rect(self.screen, COLOR_HUD, (0, 0, config.SCREEN_WIDTH, config.HUD_HEIGHT))

        left = self.font_small.render(mode_label, True, COLOR_MUTED)
        self.screen.blit(left, (12, 12))
        status_color = COLOR_SELECT if "Streak" in status else COLOR_TEXT
        self._blit_mixed_line(
            status, status_color, 12, align="right", latin_font=self.font_small
        )

        if prompt_style == "pinyin":
            _prompt_font, prompt_surf = self._fit_pinyin_prompt(char)
        elif prompt_style == "latin":
            _prompt_font, prompt_surf = self._fit_pinyin_prompt(char)
        else:
            _prompt_font, prompt_surf = self._fit_prompt(char)
        self.screen.blit(
            prompt_surf,
            (config.SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, 52),
        )

        if prompt_hint:
            hint_surf = self.font.render(prompt_hint, True, COLOR_MUTED)
            self.screen.blit(
                hint_surf,
                (config.SCREEN_WIDTH // 2 - hint_surf.get_width() // 2, 132),
            )

        self._blit_level_label(level_label)

        start_y = 188 if prompt_hint else 168
        for i, choice in enumerate(choices):
            y = start_y + i * (config.OPTION_HEIGHT + config.OPTION_GAP)
            rect = pygame.Rect(60, y, config.SCREEN_WIDTH - 120, config.OPTION_HEIGHT)
            selected_row = i == selected
            bg = COLOR_SELECT_BG if selected_row else COLOR_OPTION
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            if selected_row:
                pygame.draw.rect(self.screen, COLOR_SELECT, rect, 2, border_radius=8)
            shown = _truncate(chinese_display(choice) if chinese_choices else choice)
            if config.is_handheld():
                prefix = "> " if selected_row else "  "
                label = prefix + shown
            else:
                label = f"[{i + 1}] {shown}"
            choice_font = self.font_cjk_normal if chinese_choices else self._choice_font(shown)
            text = choice_font.render(
                label, True, COLOR_SELECT if selected_row else COLOR_TEXT
            )
            self.screen.blit(text, (rect.x + 16, rect.centery - text.get_height() // 2))

        if feedback:
            color = COLOR_CORRECT if feedback_ok else COLOR_WRONG
            self._blit_feedback(feedback, color, config.SCREEN_HEIGHT - 56)

        hint = self.font_small.render(self._handheld_hint(quiz=True), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))

    def _pinyin_font(self, *, large: bool = False) -> pygame.font.Font:
        return self.font_large if large else self.font

    def _choice_font(self, text: str) -> pygame.font.Font:
        if needs_cjk_font(text):
            return self.font_cjk_normal
        return self.font

    def _text_segments(self, text: str) -> list[tuple[str, bool]]:
        segments: list[tuple[str, bool]] = []
        buf: list[str] = []
        is_cjk: bool | None = None
        for ch in text:
            cjk = is_cjk_script_char(ch)
            if is_cjk is None:
                is_cjk = cjk
                buf.append(ch)
            elif cjk == is_cjk:
                buf.append(ch)
            else:
                segments.append(("".join(buf), is_cjk))
                buf = [ch]
                is_cjk = cjk
        if buf:
            segments.append(("".join(buf), is_cjk if is_cjk is not None else False))
        return segments

    def _segment_font(self, is_cjk: bool, *, latin_font: pygame.font.Font | None = None) -> pygame.font.Font:
        if is_cjk:
            return self.font_cjk_normal
        return latin_font or self.font

    def _blit_mixed_line(
        self,
        text: str,
        color: tuple[int, int, int],
        y: int,
        *,
        align: str = "center",
        latin_font: pygame.font.Font | None = None,
        max_w: int | None = None,
    ) -> None:
        if max_w is None:
            max_w = config.SCREEN_WIDTH - 24
        segments = self._text_segments(text)
        surfaces = [
            self._segment_font(is_cjk, latin_font=latin_font).render(seg, True, color)
            for seg, is_cjk in segments
            if seg
        ]
        total_w = sum(surf.get_width() for surf in surfaces)
        if total_w > max_w:
            shown = text
            while shown and total_w > max_w:
                shown = _truncate(shown, max(8, len(shown) - 1))
                segments = self._text_segments(shown)
                surfaces = [
                    self._segment_font(is_cjk, latin_font=latin_font).render(seg, True, color)
                    for seg, is_cjk in segments
                    if seg
                ]
                total_w = sum(surf.get_width() for surf in surfaces)
        if align == "right":
            x = config.SCREEN_WIDTH - total_w - 12
        elif align == "left":
            x = 12
        else:
            x = config.SCREEN_WIDTH // 2 - total_w // 2
        for surf in surfaces:
            self.screen.blit(surf, (x, y))
            x += surf.get_width()

    def _blit_feedback(self, text: str, color: tuple[int, int, int], y: int) -> None:
        self._blit_mixed_line(text, color, y, align="center")

    def _fit_pinyin_prompt(self, text: str) -> tuple[pygame.font.Font, pygame.Surface]:
        max_w = config.SCREEN_WIDTH - 48
        for font in (self.font_large, self.font):
            surf = font.render(text, True, COLOR_CHAR)
            if surf.get_width() <= max_w:
                return font, surf
        return self.font, self.font.render(_truncate(text, 40), True, COLOR_CHAR)

    def _fit_prompt(self, text: str) -> tuple[pygame.font.Font, pygame.Surface]:
        max_w = config.SCREEN_WIDTH - 48
        for font in (self.font_cjk, self.font_cjk_large, self.font_cjk_normal):
            surf = font.render(text, True, COLOR_CHAR)
            if surf.get_width() <= max_w:
                return font, surf
        return self.font_cjk_normal, self.font_cjk_normal.render(
            _truncate(text, 24), True, COLOR_CHAR
        )

    def draw_notice(self, title: str, message: str) -> None:
        self.clear()
        title_surf = self.font_large.render(title, True, COLOR_TEXT)
        self.screen.blit(title_surf, (config.SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 120))
        y = 200
        for line in message.split("\n"):
            surf = self.font.render(line, True, COLOR_MUTED)
            self.screen.blit(surf, (config.SCREEN_WIDTH // 2 - surf.get_width() // 2, y))
            y += 28
        hint = self.font_small.render(self._handheld_hint(), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))
