"""Main application — menu and quiz screens."""

from __future__ import annotations

from typing import Any, Callable

import pygame

from game import config
from game.cards import list_deck_files, load_deck
from game.data import load_game_data
from game.deck_srs import DeckContext, DeckEndlessSession, DeckPackSession
from game.deck_store import deck_srs, load_store, save_store
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
            if action == "bpm_endless":
                self._run_quiz(EndlessSession(self.game_data), "Bopomofo", False)
            elif action == "bpm_pack":
                self._run_quiz(PackSession(self.game_data), "Bopomofo 5-Pack", True)
            elif action == "deck_endless" and self._deck_ctx:
                self._run_quiz(DeckEndlessSession(self._deck_ctx), "Characters", False)
            elif action == "deck_pack" and self._deck_ctx:
                self._run_quiz(DeckPackSession(self._deck_ctx), "Characters 5-Pack", True)
            elif action == "pick_deck":
                self._run_deck_picker()

    def _tick_cooldown(self, dt: float) -> None:
        self._nav_cooldown = max(0.0, self._nav_cooldown - dt)

    def _menu_entries(self) -> tuple[list[str], list[str]]:
        items = [
            "Bopomofo — Endless",
            "Bopomofo — 5-Pack",
        ]
        actions = ["bpm_endless", "bpm_pack"]
        deck = self.deck_store.get("last_deck", "")
        if deck and self._deck_ctx:
            short = deck if len(deck) <= 18 else deck[:15] + "…"
            items += [
                f"Characters ({short}) — Endless",
                f"Characters ({short}) — 5-Pack",
            ]
            actions += ["deck_endless", "deck_pack"]
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
            self._deck_ctx = DeckContext(deck_file, cards, srs, self.deck_store)
        except (OSError, ValueError):
            self._deck_ctx = None

    def _run_menu(self) -> str | None:
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

            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action in ("endless", "pack", "exit"):
                    if action == "exit":
                        return None
                if action in ("quit", "back") or self.input_mgr.quit_combo_held():
                    if action == "quit" or self.input_mgr.quit_combo_held():
                        return None
                    if selected == len(items) - 1:
                        return None
                if action in ("up", "down", "confirm", "back"):
                    if action in ("up", "down") and self._nav_cooldown > 0:
                        continue
                    result = self._handle_list_nav(action, selected, len(items))
                    if result == "exit":
                        return None
                    if isinstance(result, int):
                        selected = result
                    elif result == "confirm":
                        picked = actions[selected]
                        if picked == "exit":
                            return None
                        if picked in ("deck_endless", "deck_pack") and not self._deck_ctx:
                            self._show_notice("No deck loaded", "Choose Deck first.\nCopy .apkg or .txt to decks/")
                            continue
                        return picked

            if self._nav_cooldown <= 0:
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
                        picked = actions[selected]
                        if picked == "exit":
                            return None
                        if picked in ("deck_endless", "deck_pack") and not self._deck_ctx:
                            self._show_notice("No deck loaded", "Choose Deck first.\nCopy .apkg or .txt to decks/")
                            continue
                        return picked

            self.renderer.draw_menu(
                "SHILIN TRAINER",
                items,
                selected,
                f"{config.PROJECT_NAME} — RG34XXSP / PC",
                extra,
            )
            pygame.display.flip()

    def _handle_list_nav(self, action: str, selected: int, count: int) -> str | int:
        if action == "up":
            self._nav_cooldown = config.NAV_COOLDOWN
            return (selected - 1) % count
        if action == "down":
            self._nav_cooldown = config.NAV_COOLDOWN
            return (selected + 1) % count
        if action == "back":
            if config.is_handheld() or selected == count - 1:
                return "exit"
            return selected
        if action == "confirm":
            return "confirm"
        return selected

    def _run_deck_picker(self) -> None:
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
                if action in ("quit", "back") or self.input_mgr.quit_combo_held():
                    return
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
                            self._deck_ctx = DeckContext(picked, cards, srs, self.deck_store)
                            return
                        except (OSError, ValueError) as exc:
                            self._show_notice("Deck error", str(exc))
                            return

            if self._nav_cooldown <= 0:
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
                            self._deck_ctx = DeckContext(picked, cards, srs, self.deck_store)
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
                    session.save()
                    return
                if action == "back":
                    session.save()
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
                if action in ("up", "down", "confirm"):
                    if action in ("up", "down") and self._nav_cooldown > 0:
                        continue
                    selected, answered = self._handle_quiz_nav(
                        action, selected, len(question.choices)
                    )
                    if answered is not None:
                        feedback, next_q = self._submit_answer(session, answered, pack)
                        if next_q is not None:
                            question = next_q
                            selected = 0
                        feedback_timer = config.FEEDBACK_DURATION

            if not feedback and self._nav_cooldown <= 0 and self.input_mgr.quiz_input_ready():
                polled = self.input_mgr.menu_nav()
                if polled == "confirm":
                    feedback, next_q = self._submit_answer(session, selected, pack)
                    if next_q is not None:
                        question = next_q
                        selected = 0
                    feedback_timer = config.FEEDBACK_DURATION
                elif polled == "back":
                    session.save()
                    return

            level_label = f"Lv.{question.level}" if question.level > 1 else "New"
            fb_text = None
            fb_ok = None
            if feedback:
                fb_text = feedback.message
                if feedback.submessage:
                    fb_text += f" — {feedback.submessage}"
                fb_ok = feedback.correct

            self.renderer.draw_quiz(
                mode_label,
                status_fn(),
                question.char,
                level_label,
                question.choices,
                selected,
                fb_text,
                fb_ok,
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
