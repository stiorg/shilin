"""Drawing routines for menus and quiz screens."""

from __future__ import annotations

import os

import pygame

from game import config
from game.deck_store import chinese_display
from game.pinyin import build_reading, has_pinyin_marks, is_cjk_script_char, needs_cjk_font

COLOR_BG = (24, 28, 42)
COLOR_HUD = (18, 22, 34)
COLOR_TEXT = (230, 235, 245)
COLOR_MUTED = (140, 150, 170)
COLOR_SELECT = (255, 210, 80)
COLOR_SELECT_BG = (55, 65, 95)
COLOR_OPTION = (36, 42, 62)
COLOR_CORRECT = (80, 200, 120)
COLOR_WRONG = (255, 95, 90)
COLOR_WRONG_PANEL = (52, 30, 36)
COLOR_CHAR = (255, 245, 220)
CHOICE_MAX_LEN = 34


def _truncate(text: str, max_len: int = CHOICE_MAX_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _font_log(msg: str) -> None:
    if os.environ.get("MUOS") != "1":
        return
    line = f"[shilin] font: {msg}\n"
    for rel in ("log.txt",):
        path = os.path.join(_project_root(), rel)
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
            return
        except OSError:
            continue


def _cjk_font_candidates() -> list[str]:
    root = _project_root()
    bundled = (
        "NotoSansCJKtc-Regular.otf",
        "NotoSansTC-Regular.otf",
        "NotoSansBopomofo-Regular.ttf",
    )
    paths = [os.path.join(root, "fonts", name) for name in bundled]
    paths += [
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/opt/muos/share/fonts/NotoSansCJKtc-Regular.otf",
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/msjhbd.ttc",
        "C:/Windows/Fonts/NotoSansTC-Regular.otf",
    ]
    return paths


def _latin_font_candidates() -> list[str]:
    root = _project_root()
    return [
        os.path.join(root, "fonts", "NotoSans-Regular.ttf"),
        os.path.join(root, "fonts", "NotoSans-Regular.otf"),
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/opt/muos/share/fonts/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]


def _load_from_paths(
    paths: list[str], size: int, *, label: str = "font"
) -> tuple[pygame.font.Font | None, str | None]:
    for path in paths:
        if not os.path.isfile(path):
            continue
        if path.lower().endswith(".ttc"):
            for index in range(6):
                try:
                    font = pygame.font.Font(path, size, index=index)
                    _font_log(f"{label} loaded {path} index={index} size={size}")
                    return font, path
                except (OSError, pygame.error, TypeError):
                    continue
            continue
        try:
            font = pygame.font.Font(path, size)
            _font_log(f"{label} loaded {path} size={size}")
            return font, path
        except (OSError, pygame.error):
            continue
    return None, None


def _sysfont_names(*, cjk: bool) -> tuple[str, ...]:
    if cjk:
        return (
            "noto sans cjk tc",
            "noto sans tc",
            "noto sans cjk",
            "noto sans traditional chinese",
            "microsoft jhenghei",
            "microsoft yahei",
            "arial unicode ms",
            "droid sans fallback",
            "wqy-zenhei",
        )
    return (
        "noto sans",
        "dejavu sans",
        "liberation sans",
        "segoe ui",
        "arial",
        "calibri",
        "consolas",
    )


def _load_cjk_font(size: int, bold: bool = False) -> pygame.font.Font:
    font, path = _load_from_paths(_cjk_font_candidates(), size, label="cjk")
    if font is not None:
        return font
    for name in _sysfont_names(cjk=True):
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            _font_log(f"cjk SysFont {name!r} size={size}")
            return font
        except (OSError, pygame.error):
            continue
    _font_log(f"cjk fallback bitmap size={size} (no CJK font found)")
    return pygame.font.Font(None, size + (6 if bold else 0))


def _load_latin_font(size: int, bold: bool = False) -> pygame.font.Font:
    font, _path = _load_from_paths(_latin_font_candidates(), size, label="latin")
    if font is not None:
        return font
    for name in _sysfont_names(cjk=False):
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            _font_log(f"latin SysFont {name!r} size={size}")
            return font
        except (OSError, pygame.error):
            continue
    _font_log(f"latin fallback bitmap size={size} (no Latin font found)")
    return pygame.font.Font(None, size + (6 if bold else 0))


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
                return "D-pad - Move | A - Confirm | B - Back | Hold Start+Select - Exit"
            return "1-5 - Answer | D-pad+Enter - Select | Esc - Back"
        if config.is_handheld():
            return "Hold Start+Select - Exit | B - Back"
        return "Esc - Back | Enter - Select"

    def draw_menu(
        self,
        title: str,
        items: list[str],
        selected: int,
        subtitle: str = "",
        extra: str = "",
        footer_hint: str = "",
        deck_label: str = "",
    ) -> None:
        self.clear()
        pygame.draw.rect(self.screen, COLOR_HUD, (0, 0, config.SCREEN_WIDTH, config.HUD_HEIGHT))

        title_surf = self.font_large.render(title, True, COLOR_TEXT)
        y = 28
        self.screen.blit(
            title_surf, (config.SCREEN_WIDTH // 2 - title_surf.get_width() // 2, y)
        )
        y += title_surf.get_height() + 10

        if deck_label:
            shown = _truncate(deck_label, 44)
            deck_surf = self.font_small.render(f"Deck: {shown}", True, COLOR_MUTED)
            self.screen.blit(
                deck_surf, (config.SCREEN_WIDTH // 2 - deck_surf.get_width() // 2, y)
            )
            y += deck_surf.get_height() + 8
        elif subtitle:
            sub = self.font_small.render(subtitle, True, COLOR_MUTED)
            self.screen.blit(sub, (config.SCREEN_WIDTH // 2 - sub.get_width() // 2, y))
            y += sub.get_height() + 8

        if extra:
            extra_surf = self.font.render(extra, True, COLOR_SELECT)
            self.screen.blit(
                extra_surf, (config.SCREEN_WIDTH // 2 - extra_surf.get_width() // 2, y)
            )
            y += extra_surf.get_height() + 10

        start_y = y + 4
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
            return "Up/Down - Tone | L/R - Syllable | A - Check | B - Back"
        return "Up/Down - Tone | L/R - Syllable | Enter - Check | Esc - Back"

    def _quiz_footer_reserve(self) -> int:
        return 34

    def _quiz_option_metrics(self, choice_count: int) -> tuple[int, int, int]:
        if config.is_handheld() and choice_count >= 5:
            opt_h, gap = 44, 4
        else:
            opt_h, gap = config.OPTION_HEIGHT, config.OPTION_GAP
        return opt_h, gap, opt_h + gap

    def _quiz_max_prompt_height(
        self, choice_count: int, *, hint_lines: int = 0
    ) -> tuple[int, int]:
        """Max prompt height and Y where choices begin."""
        footer = self._quiz_footer_reserve()
        level_h = self.font_small.get_height()
        opt_h, opt_gap, row_step = self._quiz_option_metrics(choice_count)
        choices_h = choice_count * row_step - opt_gap
        choices_start = config.SCREEN_HEIGHT - footer - choices_h
        hint_extra = hint_lines * (self.font.get_height() + 6)
        max_h = choices_start - config.HUD_HEIGHT - level_h - hint_extra - 20
        return max(28, max_h), choices_start

    def _quiz_prompt_y(self, prompt_h: int, choices_start: int, *, hint_lines: int = 0) -> tuple[int, int]:
        level_h = self.font_small.get_height()
        hint_extra = hint_lines * (self.font.get_height() + 6) if hint_lines else 0
        gap = 8
        level_y = choices_start - gap - level_h
        prompt_y = level_y - gap - hint_extra - prompt_h
        min_y = config.HUD_HEIGHT + 4
        if prompt_y < min_y:
            prompt_y = min_y
        return prompt_y, level_y

    def _wrap_text_lines(
        self, text: str, font: pygame.font.Font, max_w: int, max_lines: int = 2
    ) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if font.size(trial)[0] <= max_w:
                current = trial
                continue
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
            lines[-1] = _truncate(lines[-1], max(12, len(lines[-1]) - 4))
        return lines or [_truncate(text, 40)]

    def _draw_answer_wrong_panel(
        self,
        rect: pygame.Rect,
        answer: str,
        note: str = "",
    ) -> None:
        pygame.draw.rect(self.screen, COLOR_WRONG_PANEL, rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_WRONG, rect, 3, border_radius=10)

        y = rect.y + 12
        wrong = self.font_large.render("Wrong", True, COLOR_WRONG)
        self.screen.blit(wrong, (rect.centerx - wrong.get_width() // 2, y))
        y += wrong.get_height() + 10

        label = self.font_small.render("Answer", True, COLOR_MUTED)
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, y))
        y += label.get_height() + 6

        line_h = self.font.get_height() + 4
        max_w = rect.width - 28
        for line in self._wrap_text_lines(answer, self.font, max_w, max_lines=2):
            self._blit_mixed_line(
                line,
                COLOR_TEXT,
                y,
                align="center",
                max_w=max_w,
            )
            y += line_h

        if note:
            note_surf = self.font_small.render(_truncate(note, 40), True, COLOR_MUTED)
            note_y = rect.bottom - note_surf.get_height() - 10
            self.screen.blit(
                note_surf,
                (rect.centerx - note_surf.get_width() // 2, note_y),
            )

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
        feedback_note: str = "",
        correct_reading: str = "",
        your_reading: str = "",
    ) -> None:
        self.clear()
        pygame.draw.rect(self.screen, COLOR_HUD, (0, 0, config.SCREEN_WIDTH, config.HUD_HEIGHT))

        left = self.font_small.render(mode_label, True, COLOR_MUTED)
        self.screen.blit(left, (12, 12))
        status_color = COLOR_SELECT if "Streak" in status else COLOR_TEXT
        self._blit_mixed_line(
            status, status_color, 12, align="right", latin_font=self.font_small
        )

        syllable_start_y = 228
        max_prompt_h = syllable_start_y - config.HUD_HEIGHT - self.font_small.get_height() - 24
        _prompt_font, prompt_surf = self._fit_prompt(char, max_height=max(28, max_prompt_h))
        prompt_y, level_y = self._quiz_prompt_y(prompt_surf.get_height(), syllable_start_y)
        self.screen.blit(
            prompt_surf,
            (config.SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, prompt_y),
        )

        self._blit_level_label(level_label, level_y)

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
            panel_top = 196
            panel_rect = pygame.Rect(
                36,
                panel_top,
                config.SCREEN_WIDTH - 72,
                config.SCREEN_HEIGHT - self._quiz_footer_reserve() - panel_top - 8,
            )
            self._draw_tone_wrong_panel(panel_rect, correct_reading, feedback_note)
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

    def _draw_tone_wrong_panel(
        self,
        rect: pygame.Rect,
        correct_reading: str,
        note: str = "",
    ) -> None:
        pygame.draw.rect(self.screen, COLOR_WRONG_PANEL, rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_WRONG, rect, 3, border_radius=10)

        y = rect.y + 12
        label = self.font_large.render("Wrong", True, COLOR_WRONG)
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, y))
        y += label.get_height() + 12

        cap = self.font_small.render("Correct reading", True, COLOR_MUTED)
        self.screen.blit(cap, (rect.centerx - cap.get_width() // 2, y))
        y += cap.get_height() + 8

        correct_parts = correct_reading.split()
        self._draw_syllable_row(correct_parts, y, COLOR_CORRECT, highlight=True)

        if note:
            note_surf = self.font_small.render(_truncate(note, 40), True, COLOR_MUTED)
            self.screen.blit(
                note_surf,
                (rect.centerx - note_surf.get_width() // 2, rect.bottom - note_surf.get_height() - 10),
            )

    def _blit_level_label(self, level_label: str, y: int) -> None:
        surf = self.font_small.render(level_label, True, COLOR_MUTED)
        self.screen.blit(surf, (12, y))

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
        feedback_answer: str = "",
        feedback_note: str = "",
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

        hint_lines = 1 if prompt_hint else 0
        max_prompt_h, choices_start = self._quiz_max_prompt_height(
            len(choices), hint_lines=hint_lines
        )
        if prompt_style == "pinyin":
            _prompt_font, prompt_surf = self._fit_pinyin_prompt(char)
        elif prompt_style == "latin":
            _prompt_font, prompt_surf = self._fit_pinyin_prompt(char)
        else:
            _prompt_font, prompt_surf = self._fit_prompt(char, max_height=max_prompt_h)
        prompt_y, level_y = self._quiz_prompt_y(
            prompt_surf.get_height(), choices_start, hint_lines=hint_lines
        )
        self.screen.blit(
            prompt_surf,
            (config.SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, prompt_y),
        )

        if prompt_hint:
            hint_surf = self.font.render(prompt_hint, True, COLOR_MUTED)
            hint_y = level_y - hint_surf.get_height() - 6
            self.screen.blit(
                hint_surf,
                (config.SCREEN_WIDTH // 2 - hint_surf.get_width() // 2, hint_y),
            )

        self._blit_level_label(level_label, level_y)

        opt_h, opt_gap, row_step = self._quiz_option_metrics(len(choices))
        show_wrong = feedback_ok is False and bool(feedback_answer)
        if show_wrong:
            panel_rect = pygame.Rect(
                36,
                choices_start,
                config.SCREEN_WIDTH - 72,
                config.SCREEN_HEIGHT - self._quiz_footer_reserve() - choices_start - 8,
            )
            self._draw_answer_wrong_panel(
                panel_rect,
                feedback_answer or "?",
                feedback_note,
            )
        else:
            for i, choice in enumerate(choices):
                y = choices_start + i * row_step
                rect = pygame.Rect(60, y, config.SCREEN_WIDTH - 120, opt_h)
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
                self._blit_choice_label(
                    label,
                    COLOR_SELECT if selected_row else COLOR_TEXT,
                    rect,
                    chinese_only=chinese_choices,
                )

        if feedback and feedback_ok is not False:
            color = COLOR_CORRECT if feedback_ok else COLOR_WRONG
            self._blit_feedback(feedback, color, config.SCREEN_HEIGHT - 56)

        hint = self.font_small.render(self._handheld_hint(quiz=True), True, COLOR_MUTED)
        self.screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT - 28))

    def _pinyin_font(self, *, large: bool = False) -> pygame.font.Font:
        return self.font_large if large else self.font

    def _choice_font(self, text: str) -> pygame.font.Font:
        if needs_cjk_font(text) and not has_pinyin_marks(text):
            return self.font_cjk_normal
        return self.font

    def _blit_choice_label(
        self,
        label: str,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        *,
        chinese_only: bool = False,
    ) -> None:
        if chinese_only:
            surf = self.font_cjk_normal.render(label, True, color)
            self.screen.blit(surf, (rect.x + 16, rect.centery - surf.get_height() // 2))
            return
        line_h = self.font.get_height()
        y = rect.centery - line_h // 2
        self._blit_mixed_line(
            label,
            color,
            y,
            align="left",
            x=rect.x + 16,
            latin_font=self.font,
            max_w=rect.width - 32,
        )

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
        x: int | None = None,
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
        if x is not None:
            start_x = x
        elif align == "right":
            start_x = config.SCREEN_WIDTH - total_w - 12
        elif align == "left":
            start_x = 12
        else:
            start_x = config.SCREEN_WIDTH // 2 - total_w // 2
        for surf in surfaces:
            self.screen.blit(surf, (start_x, y))
            start_x += surf.get_width()

    def _blit_feedback(self, text: str, color: tuple[int, int, int], y: int) -> None:
        self._blit_mixed_line(text, color, y, align="center")

    def _fit_pinyin_prompt(self, text: str) -> tuple[pygame.font.Font, pygame.Surface]:
        max_w = config.SCREEN_WIDTH - 48
        for font in (self.font_large, self.font):
            surf = font.render(text, True, COLOR_CHAR)
            if surf.get_width() <= max_w:
                return font, surf
        return self.font, self.font.render(_truncate(text, 40), True, COLOR_CHAR)

    def _fit_prompt(
        self, text: str, *, max_height: int | None = None
    ) -> tuple[pygame.font.Font, pygame.Surface]:
        max_w = config.SCREEN_WIDTH - 48
        fonts = (self.font_cjk, self.font_cjk_large, self.font_cjk_normal)
        smallest_fit: tuple[pygame.font.Font, pygame.Surface] | None = None
        for font in fonts:
            surf = font.render(text, True, COLOR_CHAR)
            if surf.get_width() > max_w:
                continue
            if max_height is None or surf.get_height() <= max_height:
                return font, surf
            if smallest_fit is None or surf.get_height() < smallest_fit[1].get_height():
                smallest_fit = (font, surf)
        if smallest_fit is not None:
            return smallest_fit
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
