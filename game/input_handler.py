"""Keyboard and gamepad input for PC and muOS handheld."""

from __future__ import annotations

import pygame

from game import config

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_z, pygame.K_SPACE)
CONFIRM_BUTTONS = (1, 0, 2, 3, 7)
SELECT_BUTTONS = (6,)
START_BUTTONS = (7,)

# PC only — direct answer via number row
PICK_KEYS: dict[int, int] = {
    pygame.K_1: 0,
    pygame.K_2: 1,
    pygame.K_3: 2,
    pygame.K_4: 3,
    pygame.K_5: 4,
}

MENU_KEYS: dict[int, str] = {
    pygame.K_1: "endless",
    pygame.K_2: "pack",
    pygame.K_0: "exit",
}


def _event_joy_id(event: pygame.event.Event) -> int:
    if hasattr(event, "joy"):
        return int(event.joy)
    if hasattr(event, "device_index"):
        return int(event.device_index)
    return int(getattr(event, "instance_id", -1))


def _any_button(joy: pygame.joystick.Joystick, indices: tuple[int, ...]) -> bool:
    n = joy.get_numbuttons()
    return any(i < n and joy.get_button(i) for i in indices)


class InputManager:
    def __init__(self) -> None:
        self.joysticks: list[pygame.joystick.Joystick] = []
        self._held_buttons: set[tuple[int, int]] = set()
        self._quit_combo_armed = True
        self._quiz_armed = False
        self._hat_state: dict[int, tuple[int, int]] = {}
        self._refresh_joysticks()

    def arm_for_quiz(self) -> None:
        """Wait for menu confirm keys to release before accepting answers."""
        self._quiz_armed = False

    def quiz_input_ready(self) -> bool:
        if self._quiz_armed:
            return True
        if self._confirm_held():
            return False
        self._quiz_armed = True
        return True

    def _confirm_held(self) -> bool:
        keys = pygame.key.get_pressed()
        if any(keys[k] for k in CONFIRM_KEYS):
            return True
        for joy in self.joysticks:
            if _any_button(joy, CONFIRM_BUTTONS):
                return True
        return False

    def _refresh_joysticks(self) -> None:
        self.joysticks = []
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            self.joysticks.append(joy)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if getattr(event, "repeat", 0):
                return None
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key in CONFIRM_KEYS:
                return "confirm"
            if not config.is_handheld():
                if event.key in PICK_KEYS:
                    return f"pick_{PICK_KEYS[event.key]}"
                if event.key in MENU_KEYS:
                    return MENU_KEYS[event.key]
            if event.key in (pygame.K_UP, pygame.K_LEFT):
                return "up"
            if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                return "down"
        if event.type == pygame.JOYHATMOTION:
            joy_id = _event_joy_id(event)
            hx, hy = event.value
            prev = self._hat_state.get(joy_id, (0, 0))
            self._hat_state[joy_id] = (hx, hy)
            if (hx, hy) == (0, 0) or (hx, hy) == prev:
                return None
            if hy == 1:
                return "up"
            if hy == -1:
                return "down"
            if hx == -1:
                return "up"
            if hx == 1:
                return "down"
        if event.type == pygame.JOYBUTTONDOWN:
            self._held_buttons.add((_event_joy_id(event), event.button))
            if event.button in SELECT_BUTTONS:
                return "back"
            if event.button in CONFIRM_BUTTONS:
                return "confirm"
        if event.type == pygame.JOYBUTTONUP:
            self._held_buttons.discard((_event_joy_id(event), event.button))
        if event.type == pygame.JOYDEVICEADDED:
            self._refresh_joysticks()
        if event.type == pygame.JOYDEVICEREMOVED:
            removed = _event_joy_id(event)
            self._held_buttons = {pair for pair in self._held_buttons if pair[0] != removed}
            self._refresh_joysticks()
        return None

    def _button_held(self, joy_idx: int, joy: pygame.joystick.Joystick, indices: tuple[int, ...]) -> bool:
        if _any_button(joy, indices):
            return True
        return any(pair[0] == joy_idx and pair[1] in indices for pair in self._held_buttons)

    def menu_nav(self) -> str | None:
        """Poll confirm/back only — navigation is edge-triggered via events."""
        keys = pygame.key.get_pressed()
        if any(keys[k] for k in CONFIRM_KEYS):
            return "confirm"
        if keys[pygame.K_ESCAPE]:
            return "back"

        for joy_idx, joy in enumerate(self.joysticks):
            if self._button_held(joy_idx, joy, CONFIRM_BUTTONS[:4]):
                return "confirm"
            if _any_button(joy, SELECT_BUTTONS):
                return "back"
        return None

    def quit_combo_held(self) -> bool:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] and keys[pygame.K_RETURN]:
            if self._quit_combo_armed:
                self._quit_combo_armed = False
                return True
            return False
        for joy in self.joysticks:
            if joy.get_numbuttons() > 7 and joy.get_button(6) and joy.get_button(7):
                if self._quit_combo_armed:
                    self._quit_combo_armed = False
                    return True
                return False
        self._quit_combo_armed = True
        return False
