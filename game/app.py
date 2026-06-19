"""Main application — menu and quiz screens."""

from __future__ import annotations

import pygame

from game import config
from game.data import load_game_data
from game.input_handler import InputManager
from game.renderer import Renderer
from game.srs import AnswerResult, EndlessSession, PackSession


class App:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.renderer = Renderer(screen)
        self.input_mgr = InputManager()
        self.game_data = load_game_data()
        self._nav_cooldown = 0.0

    def run(self) -> None:
        while True:
            mode = self._run_menu()
            if mode is None:
                break
            if mode == "endless":
                self._run_endless()
            elif mode == "pack":
                self._run_pack()

    def _tick_cooldown(self, dt: float) -> None:
        self._nav_cooldown = max(0.0, self._nav_cooldown - dt)

    def _run_menu(self) -> str | None:
        items = [
            "Endless SRS Streak Mode",
            "Focused SRS 5-Pack Mode",
            "Exit",
        ]
        selected = 0
        clock = pygame.time.Clock()
        high = self.game_data["all_time_high_streak"]
        extra = f"All-Time Max Streak: {high}"

        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)

            for event in pygame.event.get():
                action = self.input_mgr.handle_event(event)
                if action in ("endless", "pack", "exit"):
                    if action == "exit":
                        return None
                    return action
                if action in ("quit", "back") or self.input_mgr.quit_combo_held():
                    if selected == 2 or action == "quit" or self.input_mgr.quit_combo_held():
                        return None
                if action in ("up", "down", "confirm", "back"):
                    result = self._handle_menu_nav(action, selected, items)
                    if result == "exit":
                        return None
                    if result in ("endless", "pack"):
                        return result
                    if isinstance(result, int):
                        selected = result

            if self._nav_cooldown <= 0:
                if self.input_mgr.quit_combo_held():
                    return None
                polled = self.input_mgr.menu_nav()
                if polled:
                    result = self._handle_menu_nav(polled, selected, items)
                    if result == "exit":
                        return None
                    if result in ("endless", "pack"):
                        return result
                    if isinstance(result, int):
                        selected = result

            self.renderer.draw_menu(
                "BOPOMOFO",
                items,
                selected,
                "Training Center — RG34XXSP / PC",
                extra,
            )
            pygame.display.flip()

    def _handle_menu_nav(self, action: str, selected: int, items: list[str]) -> str | int | None:
        if action == "up":
            self._nav_cooldown = 0.15
            return (selected - 1) % len(items)
        if action == "down":
            self._nav_cooldown = 0.15
            return (selected + 1) % len(items)
        if action == "back":
            if config.is_handheld() or selected == len(items) - 1:
                return "exit"
            return selected
        if action == "confirm":
            if selected == 0:
                return "endless"
            if selected == 1:
                return "pack"
            return "exit"
        return None

    def _run_endless(self) -> None:
        session = EndlessSession(self.game_data)
        question = session.next_question()
        selected = 0
        feedback: AnswerResult | None = None
        feedback_timer = 0.0
        clock = pygame.time.Clock()

        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)

            if feedback:
                feedback_timer -= dt
                if feedback_timer <= 0:
                    feedback = None
                    question = session.next_question()
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
                picked = self._parse_pick(action)
                if picked is not None:
                    selected = picked
                    feedback = session.answer(picked)
                    if feedback.new_high_streak:
                        feedback.submessage = "NEW ALL-TIME HIGH STREAK!"
                    feedback_timer = config.FEEDBACK_DURATION
                    continue
                if action in ("up", "down", "confirm"):
                    selected, answered = self._handle_quiz_nav(
                        action, selected, len(question.choices)
                    )
                    if answered is not None:
                        feedback = session.answer(answered)
                        if feedback.new_high_streak:
                            feedback.submessage = "NEW ALL-TIME HIGH STREAK!"
                        feedback_timer = config.FEEDBACK_DURATION

            if not feedback and self._nav_cooldown <= 0:
                polled = self.input_mgr.menu_nav()
                if polled in ("up", "down"):
                    selected, _ = self._handle_quiz_nav(polled, selected, len(question.choices))
                elif polled == "confirm":
                    feedback = session.answer(selected)
                    if feedback.new_high_streak:
                        feedback.submessage = "NEW ALL-TIME HIGH STREAK!"
                    feedback_timer = config.FEEDBACK_DURATION
                elif polled == "back":
                    session.save()
                    return

            level_label = f"Lv.{question.level}" if question.level > 1 else "New"
            streak = f"Streak: {session.current_streak}" if session.current_streak else ""
            fb_text = None
            fb_ok = None
            if feedback:
                fb_text = feedback.message
                if feedback.submessage:
                    fb_text += f" — {feedback.submessage}"
                fb_ok = feedback.correct

            self.renderer.draw_quiz(
                "Endless SRS",
                streak,
                question.char,
                level_label,
                question.choices,
                selected,
                fb_text,
                fb_ok,
            )
            pygame.display.flip()

    def _run_pack(self) -> None:
        session = PackSession(self.game_data)
        question = session.next_question()
        selected = 0
        feedback: AnswerResult | None = None
        feedback_timer = 0.0
        clock = pygame.time.Clock()

        while True:
            dt = clock.tick(config.FPS) / 1000.0
            self._tick_cooldown(dt)

            if feedback:
                feedback_timer -= dt
                if feedback_timer <= 0:
                    feedback = None
                    if session.all_done:
                        return
                    question = session.next_question()
                    if question is None:
                        return
                    selected = 0

            if question is None:
                return

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
                picked = self._parse_pick(action)
                if picked is not None:
                    selected = picked
                    feedback = session.answer(picked)
                    if feedback.new_high_streak:
                        feedback.submessage = "NEW ALL-TIME HIGH STREAK!"
                    feedback_timer = config.FEEDBACK_DURATION
                    continue
                if action in ("up", "down", "confirm"):
                    selected, answered = self._handle_quiz_nav(
                        action, selected, len(question.choices)
                    )
                    if answered is not None:
                        feedback = session.answer(answered)
                        if session.pack_cleared and feedback.correct:
                            feedback.submessage = f"Pack #{session.pack_count - 1} cleared!"
                        feedback_timer = config.FEEDBACK_DURATION

            if not feedback and self._nav_cooldown <= 0:
                polled = self.input_mgr.menu_nav()
                if polled in ("up", "down"):
                    selected, _ = self._handle_quiz_nav(polled, selected, len(question.choices))
                elif polled == "confirm":
                    feedback = session.answer(selected)
                    if session.pack_cleared and feedback.correct:
                        feedback.submessage = f"Pack #{session.pack_count - 1} cleared!"
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
                "5-Pack SRS",
                session.pack_label()[:48],
                question.char,
                level_label,
                question.choices,
                selected,
                fb_text,
                fb_ok,
            )
            pygame.display.flip()

    def _parse_pick(self, action: str | None) -> int | None:
        if action and action.startswith("pick_"):
            return int(action[5:])
        return None

    def _handle_quiz_nav(
        self, action: str, selected: int, count: int
    ) -> tuple[int, int | None]:
        if action == "up":
            self._nav_cooldown = 0.12
            return (selected - 1) % count, None
        if action == "down":
            self._nav_cooldown = 0.12
            return (selected + 1) % count, None
        if action == "confirm":
            return selected, selected
        return selected, None
