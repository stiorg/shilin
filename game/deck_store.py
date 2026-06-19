"""SRS persistence for Anki / character decks."""

from __future__ import annotations

import json
import os
import random

from game.cards import Card, ROOT

DATA_FILE = os.path.join(ROOT, "flashcard_srs_data.json")


def load_store() -> dict:
    default = {"last_deck": "", "decks": {}}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
                if "decks" in data:
                    return data
        except (OSError, json.JSONDecodeError):
            pass
    return default


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


def generate_choices(correct: str, card_id: str, srs: dict, pool: list[str]) -> list[str]:
    choices = [correct]
    mistakes = srs["confusion_matrix"].get(card_id, []).copy()
    mistakes = list(dict.fromkeys(reversed(mistakes)))
    for mistake in mistakes:
        if mistake != correct and mistake not in choices:
            choices.append(mistake)
        if len(choices) == 5:
            break
    answers = list({a for a in pool if a})
    while len(choices) < 5 and answers:
        pick = random.choice(answers)
        if pick not in choices:
            choices.append(pick)
    random.shuffle(choices)
    return choices
