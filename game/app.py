"""Main application — menu and quiz screens."""

from __future__ import annotations

from typing import Any, Callable

import pygame

from game import config
from game.cards import list_deck_files, load_deck
from game.data import load_game_data, save_game_data
from game.deck_modes import (
    DECK_MODE_LABELS,
    cycle_mode,
    is_tone_mode,
    requires_meaning,
    uses_chinese_choices,
    uses_latin_prompt,
    uses_pinyin_prompt,
)
from game.deck_srs import DeckContext, DeckEndlessSession, DeckPackSession, ToneDrill
from game.deck_store import deck_mode, deck_srs, load_store, save_store
from game.input_handler import InputManager
from game.renderer import Renderer
from game.srs import AnswerResult, EndlessSession, PackSession


class App:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.renderer = Renderer(screen)
        self.input_mgr = InputManager()
        self.game_data = load_game_data()
        self.deck_store = load_store()
        self._nav_cooldown = 0.0
        self._deck_ctx: DeckContext | None = None

    def run(self) -> None:
        while True:
            action = self._run_menu()
            if action is None:
                break
            if action == "bpm":
                pack = self._bpm_pack_mode()
                session = PackSession(self.game_data) if pack else EndlessSession(self.game_data)
                label = "Bopomofo" + (" · 5-Pack" if pack else "")
                self._run_quiz(session, label, pack)
            elif action == "deck" and self._deck_ctx:
                self._start_deck_session(self._deck_pack_mode())
            elif action == "pick_deck":
                self._run_deck_picker()

    def _tick_cooldown(self, dt: float) -> None:
        self._nav_cooldown = max(0.0, self._nav_cooldown - dt)

    def _srs_layout_label(self, pack: bool) -> str:
        return "5-Pack" if pack else "Endless"

    def _bpm_pack_mode(self) -> bool:
        return bool(self.game_data.get("pack_mode", False))

    def _deck_pack_mode(self) -> bool:
        return bool(self.deck_store.get("pack_mode", False))

    def _toggle_bpm_pack_mode(self) -> None:
        self.game_data["pack_mode"] = not self._bpm_pack_mode()
        save_game_data(self.game_data)
        self._nav_cooldown = config.NAV_COOLDOWN

    def _toggle_deck_pack_mode(self) -> None:
        self.deck_store["pack_mode"] = not self._deck_pack_mode()
        save_store(self.deck_store)
        self._nav_cooldown = config.NAV_COOLDOWN

    def _deck_mode_label(self) -> str:
        return f"Characters · {DECK_MODE_LABELS[deck_mode(self.deck_store)]}"

    def _start_deck_session(self, pack: bool) -> None:
        ctx = self._deck_ctx
        if ctx is None:
            return
        if requires_meaning(ctx.mode) and not ctx.meanings:
            self._show_notice(
                "No translations in deck",
                "Translate modes need a 3rd field\n"
                "(English / meaning in Anki export)",
            )
            return
        label = self._deck_mode_label()
        if pack:
            label = f"{label} 5-Pack"
            session = DeckPackSession(ctx)
        else:
            session = DeckEndlessSession(ctx)
        if is_tone_mode(ctx.mode):
            self._run_tone_quiz(session, label, pack)
        else:
            self._run_quiz(session, label, pack)

    def _deck_prompt_style(self, mode: str) -> str:
        if uses_pinyin_prompt(mode):
            return "pinyin"
        if uses_latin_prompt(mode):
            return "latin"
        return "chinese"

    def _is_drill_menu_index(self, actions: list[str], selected: int) -> bool:
        if selected < 0 or selected >= len(actions):
            return False
        return actions[selected] in ("bpm", "deck")

    def _is_deck_menu_index(self, actions: list[str], selected: int) -> bool:
        if selected < 0 or selected >= len(actions):
            return False
        return actions[selected] == "deck"

    def _cycle_deck_mode(self, delta: int) -> None:
        self.deck_store["deck_mode"] = cycle_mode(deck_mode(self.deck_store), delta)
        if self._deck_ctx is not None:
            self._deck_ctx.mode = self.deck_store["deck_mode"]
        save_store(self.deck_store)
        self._nav_cooldown = config.NAV_COOLDOWN

    def _menu_entries(self) -> tuple[list[str], list[str]]:
        items = [f"Bopomofo - {self._srs_layout_label(self._bpm_pack_mode())}"]
        actions = ["bpm"]
        deck = self.deck_store.get("last_deck", "")
        if deck and self._deck_ctx:
            mode = DECK_MODE_LABELS[deck_mode(self.deck_store)]
            layout = self._srs_layout_label(self._deck_pack_mode())
            items += [f"Characters - {mode} - {layout}"]
            actions += ["deck"]
        items += ["Choose Deck…", "Exit"]
        actions += ["pick_deck", "exit"]
        return items, actions

    def _ensure_deck(self) -> None:
        deck_file = self.deck_store.get("last_deck", "")
        if not deck_file:
            self._deck_ctx = None
            return
        try:
            cards = load_deck(deck_file)
            srs = deck_srs(self.deck_store, deck_file, cards)
            self._deck_ctx = DeckContext(
                deck_file, cards, srs, self.deck_store, deck_mode(self.deck_store)
            )
        except (OSError, ValueError):
            self._deck_ctx = None

    def _confirm_menu_pick(self, picked: str) -> str | None:
        if picked == "exit":
            return None
        if picked == "pick_deck":
            self._run_deck_picker()
            self._ensure_deck()
            self.input_mgr.arm_for_menu()
            return "menu"
        if picked == "deck" and not self._deck_ctx:
            self._show_notice(
                "No deck loaded",
                "Choose Deck first.\nCopy .apkg or .txt to decks/",
            )
            return "menu"
        return picked

    def _run_menu(self) -> str | None:
        self.input_mgr.set_menu_mode(True)
        self._ensure_deck()
        items, actions = self._menu_entries()
        selected = 0
        clock = pygame.time.Clock()
        high = self.game_data["all_time_high_streak"]
        deck_count = len(list_deck_files())
        extra = f"Bopomofo streak: {high}  |  Decks in decks/: {deck_count}"

        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)
            items, actions = self._menu_entries()
            menu_hint = self._menu_hint(actions, selected)

            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action and action.startswith("menu_pick_"):
                    idx = int(action[10:])
                    if idx < len(items):
                        selected = idx
                    continue
                if action == "exit":
                    return None
                if action == "toggle_pack":
                    if self._is_drill_menu_index(actions, selected):
                        if self._nav_cooldown > 0:
                            continue
                        if actions[selected] == "bpm":
                            self._toggle_bpm_pack_mode()
                        elif actions[selected] == "deck":
                            self._toggle_deck_pack_mode()
                        continue
                    action = "confirm"
                if action in ("quit", "back") or self.input_mgr.quit_combo_held():
                    if not self.input_mgr.menu_confirm_ready():
                        continue
                    if action == "quit" or self.input_mgr.quit_combo_held():
                        return None
                    if selected == len(items) - 1:
                        return None
                if action in ("left", "right") and self._is_deck_menu_index(actions, selected):
                    if self._nav_cooldown > 0:
                        continue
                    self._cycle_deck_mode(-1 if action == "left" else 1)
                    continue
                nav_action = self._menu_nav_action(action, actions, selected)
                if nav_action in ("up", "down", "confirm", "back"):
                    if nav_action in ("up", "down") and self._nav_cooldown > 0:
                        continue
                    result = self._handle_list_nav(nav_action, selected, len(items))
                    if result == "exit":
                        return None
                    if isinstance(result, int):
                        selected = result
                    elif result == "confirm":
                        picked = self._confirm_menu_pick(actions[selected])
                        if picked == "menu":
                            continue
                        if picked is None:
                            return None
                        return picked

            if self._nav_cooldown <= 0 and self.input_mgr.menu_confirm_ready():
                if self.input_mgr.quit_combo_held():
                    return None
                polled = self.input_mgr.menu_nav()
                if polled:
                    result = self._handle_list_nav(polled, selected, len(items))
                    if result == "exit":
                        return None
                    if isinstance(result, int):
                        selected = result
                    elif result == "confirm":
                        picked = self._confirm_menu_pick(actions[selected])
                        if picked == "menu":
                            continue
                        if picked is None:
                            return None
                        return picked

            deck_label = ""
            if self.deck_store.get("last_deck") and self._deck_ctx:
                deck_label = self.deck_store["last_deck"]

            self.renderer.draw_menu(
                "SHILIN TRAINER",
                items,
                selected,
                extra=extra,
                footer_hint=menu_hint,
                deck_label=deck_label,
            )
            pygame.display.flip()

    def _menu_hint(self, actions: list[str], selected: int) -> str:
        parts: list[str] = []
        if 0 <= selected < len(actions) and actions[selected] in ("bpm", "deck"):
            toggle = "X/Y" if config.is_handheld() else "Space"
            parts.append(f"{toggle} - Endless / 5-Pack")
        if 0 <= selected < len(actions) and actions[selected] == "deck":
            parts.append("L/R - Character mode")
        if not parts:
            return ""
        if config.is_handheld():
            parts.append("Start+Select - Exit | B - Back")
            return " | ".join(parts)
        parts.append("Esc - Back | Enter - Select")
        return " | ".join(parts)

    def _menu_nav_action(self, action: str, actions: list[str], selected: int) -> str | None:
        if action in ("up", "down", "confirm", "back"):
            return action
        if action in ("left", "right") and not self._is_deck_menu_index(actions, selected):
            return "up" if action == "left" else "down"
        return None

    def _leave_quiz(self, session: Any) -> None:
        session.save()
        self.input_mgr.arm_for_menu()

    def _handle_list_nav(self, action: str, selected: int, count: int) -> str | int:
        if action == "up":
            self._nav_cooldown = config.NAV_COOLDOWN
            return (selected - 1) % count
        if action == "down":
            self._nav_cooldown = config.NAV_COOLDOWN
            return (selected + 1) % count
        if action == "back":
            if selected == count - 1:
                return "exit"
            return selected
        if action == "confirm":
            return "confirm"
        return selected

    def _run_deck_picker(self) -> None:
        self.input_mgr.set_menu_mode(True)
        files = list_deck_files()
        if not files:
            self._show_notice(
                "No decks found",
                "Copy Anki decks to decks/\n"
                "  • .apkg (classic format)\n"
                "  • .txt (Anki plain-text export)",
            )
            return

        items = files + ["« Back"]
        actions = files + ["back"]
        selected = 0
        if self.deck_store.get("last_deck") in files:
            selected = files.index(self.deck_store["last_deck"])

        clock = pygame.time.Clock()
        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)

            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action and action.startswith("menu_pick_"):
                    idx = int(action[10:])
                    if idx < len(items):
                        selected = idx
                    continue
                if action in ("quit", "back") or self.input_mgr.quit_combo_held():
                    return
                if action in ("left", "right"):
                    action = "up" if action == "left" else "down"
                if action in ("up", "down", "confirm"):
                    if action in ("up", "down") and self._nav_cooldown > 0:
                        continue
                    result = self._handle_list_nav(action, selected, len(items))
                    if isinstance(result, int):
                        selected = result
                    elif result == "confirm":
                        picked = actions[selected]
                        if picked == "back":
                            return
                        try:
                            cards = load_deck(picked)
                            self.deck_store["last_deck"] = picked
                            srs = deck_srs(self.deck_store, picked, cards)
                            save_store(self.deck_store)
                            self._deck_ctx = DeckContext(
                                picked, cards, srs, self.deck_store, deck_mode(self.deck_store)
                            )
                            return
                        except (OSError, ValueError) as exc:
                            self._show_notice("Deck error", str(exc))
                            return

            if self._nav_cooldown <= 0 and self.input_mgr.menu_confirm_ready():
                polled = self.input_mgr.menu_nav()
                if polled:
                    result = self._handle_list_nav(polled, selected, len(items))
                    if isinstance(result, int):
                        selected = result
                    elif result == "confirm":
                        picked = actions[selected]
                        if picked == "back":
                            return
                        try:
                            cards = load_deck(picked)
                            self.deck_store["last_deck"] = picked
                            srs = deck_srs(self.deck_store, picked, cards)
                            save_store(self.deck_store)
                            self._deck_ctx = DeckContext(
                                picked, cards, srs, self.deck_store, deck_mode(self.deck_store)
                            )
                            return
                        except (OSError, ValueError) as exc:
                            self._show_notice("Deck error", str(exc))
                            return

            self.renderer.draw_menu(
                "CHOOSE DECK",
                items,
                selected,
                f"{len(files)} deck(s) in decks/",
            )
            pygame.display.flip()

    def _show_notice(self, title: str, message: str) -> None:
        clock = pygame.time.Clock()
        until = 2.5
        while until > 0:
            dt = clock.tick(config.FPS) / 1000.0
            until -= dt
            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action in ("quit", "back", "confirm") or self.input_mgr.quit_combo_held():
                    return
            self.renderer.draw_notice(title, message)
            pygame.display.flip()

    def _run_tone_quiz(self, session: Any, mode_label: str, pack: bool) -> None:
        self.input_mgr.arm_for_quiz()
        drill = session.next_tone_drill()
        if drill is None:
            return
        feedback: AnswerResult | None = None
        feedback_timer = 0.0
        clock = pygame.time.Clock()

        status_fn: Callable[[], str]
        if pack:
            status_fn = lambda: session.pack_label()[:48]
        else:
            status_fn = lambda: (
                f"Streak: {session.current_streak}" if session.current_streak else ""
            )

        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)

            if feedback:
                feedback_timer -= dt
                if feedback_timer <= 0:
                    feedback = None
                    if pack and getattr(session, "all_done", False):
                        session.save()
                        return
                    drill = session.next_tone_drill()
                    if drill is None:
                        session.save()
                        return

            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action == "quit" or self.input_mgr.quit_combo_held():
                    self._leave_quiz(session)
                    return
                if action == "back":
                    self._leave_quiz(session)
                    return
                if feedback:
                    continue
                if not self.input_mgr.quiz_input_ready():
                    continue
                if action == "confirm":
                    feedback, next_drill = self._submit_tone_answer(session, drill, pack)
                    if next_drill is not None:
                        drill = next_drill
                    feedback_timer = config.FEEDBACK_DURATION
                    continue
                if action in ("up", "down", "left", "right"):
                    if self._nav_cooldown > 0:
                        continue
                    self._nav_cooldown = config.NAV_COOLDOWN
                    if action == "up":
                        drill.adjust_tone(1)
                    elif action == "down":
                        drill.adjust_tone(-1)
                    elif action == "left":
                        drill.move_syllable(-1)
                    elif action == "right":
                        drill.move_syllable(1)

            if self._nav_cooldown <= 0 and self.input_mgr.quiz_input_ready():
                polled = self.input_mgr.menu_nav()
                if polled == "back":
                    self._leave_quiz(session)
                    return
                if not feedback and polled == "confirm":
                    feedback, next_drill = self._submit_tone_answer(session, drill, pack)
                    if next_drill is not None:
                        drill = next_drill
                    feedback_timer = config.FEEDBACK_DURATION

            level_label = f"Lv.{drill.level}" if drill.level > 1 else "New"
            fb_text = None
            fb_ok = None
            correct_reading = ""
            your_reading = ""
            if feedback:
                fb_ok = feedback.correct
                if feedback.correct:
                    fb_text = feedback.message
                    if feedback.submessage:
                        fb_text += f" - {feedback.submessage}"
                else:
                    correct_reading = drill.correct
                    your_reading = drill.reading()
                    fb_text = feedback.submessage or ""

            self.renderer.draw_tone_quiz(
                mode_label,
                status_fn(),
                drill.char,
                level_label,
                drill.syllables,
                drill.tones,
                drill.selected,
                fb_text,
                fb_ok,
                correct_reading,
                your_reading,
            )
            pygame.display.flip()

    def _submit_tone_answer(
        self, session: Any, drill: ToneDrill, pack: bool
    ) -> tuple[AnswerResult, ToneDrill | None]:
        feedback = session.answer_tone(drill)
        feedback = self._after_answer(session, pack, feedback)
        next_drill = self._maybe_advance_pack_tone(session, pack)
        return feedback, next_drill

    def _maybe_advance_pack_tone(self, session: Any, pack: bool) -> ToneDrill | None:
        if not pack or not getattr(session, "pack_rolled", False):
            return None
        session.pack_rolled = False
        if session.all_done:
            return None
        return session.next_tone_drill()

    def _run_quiz(self, session: Any, mode_label: str, pack: bool) -> None:
        self.input_mgr.arm_for_quiz()
        question = session.next_question()
        if question is None:
            return
        selected = 0
        feedback: AnswerResult | None = None
        feedback_timer = 0.0
        clock = pygame.time.Clock()

        status_fn: Callable[[], str]
        if pack:
            status_fn = lambda: session.pack_label()[:48]
        else:
            status_fn = lambda: (
                f"Streak: {session.current_streak}" if session.current_streak else ""
            )

        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)

            if feedback:
                feedback_timer -= dt
                if feedback_timer <= 0:
                    feedback = None
                    if pack and getattr(session, "all_done", False):
                        session.save()
                        return
                    question = session.next_question()
                    if question is None:
                        session.save()
                        return
                    selected = 0

            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action == "quit" or self.input_mgr.quit_combo_held():
                    self._leave_quiz(session)
                    return
                if action == "back":
                    self._leave_quiz(session)
                    return
                if feedback:
                    continue
                if not self.input_mgr.quiz_input_ready():
                    continue
                picked = self._parse_pick(action)
                if picked is not None:
                    feedback, next_q = self._submit_answer(session, picked, pack)
                    if next_q is not None:
                        question = next_q
                        selected = 0
                    feedback_timer = config.FEEDBACK_DURATION
                    continue
                if action in ("up", "down", "left", "right", "confirm"):
                    if action in ("up", "down", "left", "right") and self._nav_cooldown > 0:
                        continue
                    nav_action = self._quiz_nav_action(action)
                    selected, answered = self._handle_quiz_nav(
                        nav_action, selected, len(question.choices)
                    )
                    if answered is not None:
                        feedback, next_q = self._submit_answer(session, answered, pack)
                        if next_q is not None:
                            question = next_q
                            selected = 0
                        feedback_timer = config.FEEDBACK_DURATION

            if self._nav_cooldown <= 0 and self.input_mgr.quiz_input_ready():
                polled = self.input_mgr.menu_nav()
                if polled == "back":
                    self._leave_quiz(session)
                    return
                if not feedback and polled == "confirm":
                    feedback, next_q = self._submit_answer(session, selected, pack)
                    if next_q is not None:
                        question = next_q
                        selected = 0
                    feedback_timer = config.FEEDBACK_DURATION

            level_label = f"Lv.{question.level}" if question.level > 1 else "New"
            fb_text = None
            fb_ok = None
            if feedback:
                fb_text = feedback.message
                if feedback.submessage:
                    fb_text += f" - {feedback.submessage}"
                fb_ok = feedback.correct

            deck_mode_name = getattr(getattr(session, "ctx", None), "mode", "standard")
            self.renderer.draw_quiz(
                mode_label,
                status_fn(),
                question.char,
                level_label,
                question.choices,
                selected,
                fb_text,
                fb_ok,
                question.hint,
                uses_chinese_choices(deck_mode_name),
                self._deck_prompt_style(deck_mode_name),
            )
            pygame.display.flip()

    def _submit_answer(
        self, session: Any, index: int, pack: bool
    ) -> tuple[AnswerResult, Any | None]:
        feedback = session.answer(index)
        feedback = self._after_answer(session, pack, feedback)
        next_q = self._maybe_advance_pack_question(session, pack)
        return feedback, next_q

    def _after_answer(
        self, session: Any, pack: bool, feedback: AnswerResult
    ) -> AnswerResult:
        if feedback.new_high_streak:
            feedback.submessage = "NEW ALL-TIME HIGH STREAK!"
        if pack and getattr(session, "pack_rolled", False) and feedback.correct:
            session.pack_rolled = False
            feedback.submessage = f"Pack #{session.pack_count - 1} cleared!"
        return feedback

    def _maybe_advance_pack_question(self, session: Any, pack: bool) -> Any | None:
        if not pack or not getattr(session, "pack_rolled", False):
            return None
        session.pack_rolled = False
        if session.all_done:
            return None
        return session.next_question()

    def _quiz_nav_action(self, action: str) -> str:
        if action == "left":
            return "up"
        if action == "right":
            return "down"
        return action

    def _parse_pick(self, action: str | None) -> int | None:
        if action and action.startswith("pick_"):
            return int(action[5:])
        return None

    def _handle_quiz_nav(
        self, action: str, selected: int, count: int
    ) -> tuple[int, int | None]:
        if action == "up":
            self._nav_cooldown = config.NAV_COOLDOWN
            return (selected - 1) % count, None
        if action == "down":
            self._nav_cooldown = config.NAV_COOLDOWN
            return (selected + 1) % count, None
        if action == "confirm":
            return selected, selected
        return selected, None
