"""SRS persistence for Anki / character decks."""

from __future__ import annotations

import json
import os
import random

from game.cards import Card, ROOT
from game.deck_modes import normalize_mode

DATA_FILE = os.path.join(ROOT, "flashcard_srs_data.json")


def load_store() -> dict:
    default = {"last_deck": "", "deck_mode": "standard", "decks": {}}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
                if "decks" in data:
                    return data
        except (OSError, json.JSONDecodeError):
            pass
    return default


def deck_mode(store: dict) -> str:
    return normalize_mode(store.get("deck_mode"))


def save_store(store: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=False, indent=4)


def deck_srs(store: dict, deck_file: str, cards: list[Card]) -> dict:
    if deck_file not in store["decks"]:
        store["decks"][deck_file] = {
            "all_time_high_streak": 0,
            "intervals": {c.id: 1 for c in cards},
            "confusion_matrix": {c.id: [] for c in cards},
        }
    srs = store["decks"][deck_file]
    for card in cards:
        srs["intervals"].setdefault(card.id, 1)
        srs["confusion_matrix"].setdefault(card.id, [])
    return srs


def chinese_display(text: str) -> str:
    return "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")


def chinese_choice_pool(pool: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in pool:
        display = chinese_display(item)
        if display and display not in seen:
            seen.add(display)
            result.append(display)
    return result


def remember_mistake(srs: dict, card_id: str, selected: str, *, chinese_only: bool) -> None:
    if chinese_only:
        selected = chinese_display(selected)
        if not selected:
            return
    matrix = srs["confusion_matrix"].setdefault(card_id, [])
    if selected not in matrix:
        matrix.append(selected)


def generate_choices(correct: str, card_id: str, srs: dict, pool: list[str]) -> list[str]:
    choices = [correct]
    mistakes = srs["confusion_matrix"].get(card_id, []).copy()
    mistakes = list(dict.fromkeys(reversed(mistakes)))
    for mistake in mistakes:
        if chinese_display(mistake):
            continue
        if mistake != correct and mistake not in choices:
            choices.append(mistake)
        if len(choices) == 5:
            break
    answers = [a for a in pool if a and a not in choices]
    random.shuffle(answers)
    for pick in answers:
        choices.append(pick)
        if len(choices) == 5:
            break
    random.shuffle(choices)
    return choices[:5]


def generate_reverse_choices(correct: str, card_id: str, srs: dict, pool: list[str]) -> list[str]:
    correct = chinese_display(correct)
    pool = chinese_choice_pool(pool)
    if not correct:
        return pool[:5] if pool else []

    choices = [correct]
    mistakes = srs["confusion_matrix"].get(card_id, []).copy()
    mistakes = list(dict.fromkeys(reversed(mistakes)))
    for mistake in mistakes:
        display = chinese_display(mistake)
        if display and display != correct and display not in choices:
            choices.append(display)
        if len(choices) == 5:
            break

    answers = [a for a in pool if a not in choices]
    random.shuffle(answers)
    for pick in answers:
        choices.append(pick)
        if len(choices) == 5:
            break

    random.shuffle(choices)
    return choices[:5]
