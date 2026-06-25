"""SRS persistence for Anki / character decks."""

from __future__ import annotations

import json
import os
import random

from game.cards import Card, ROOT
from game.deck_modes import DECK_MODES, normalize_mode
from game.pinyin import has_pinyin_marks
from game.scheduling import ensure_schedule

DATA_FILE = os.path.join(ROOT, "flashcard_srs_data.json")


def load_store() -> dict:
    default = {"last_deck": "", "deck_mode": "standard", "pack_mode": False, "decks": {}}
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


def _fresh_mode_bucket(card_ids: list[str]) -> dict:
    return {
        "all_time_high_streak": 0,
        "intervals": {card_id: 1 for card_id in card_ids},
        "ease_factors": {card_id: 2.5 for card_id in card_ids},
        "repetitions": {card_id: 0 for card_id in card_ids},
        "last_reviewed_at": {card_id: "" for card_id in card_ids},
        "confusion_matrix": {card_id: [] for card_id in card_ids},
    }


def migrate_deck_srs(srs: dict, card_ids: list[str]) -> None:
    """Move legacy flat SRS data into per-mode buckets."""
    if "modes" in srs:
        return
    modes: dict[str, dict] = {}
    if "intervals" in srs:
        modes["standard"] = {
            "intervals": srs.pop("intervals"),
            "confusion_matrix": srs.pop("confusion_matrix", {}),
            "due": srs.pop("due", {}),
            "all_time_high_streak": int(srs.pop("all_time_high_streak", 0)),
        }
        ensure_schedule(modes["standard"], card_ids)
    srs["modes"] = modes


def mode_schedule(srs: dict, mode: str, card_ids: list[str]) -> dict:
    """SRS schedule for one study mode (standard, reverse, tone, etc.)."""
    migrate_deck_srs(srs, card_ids)
    mode = normalize_mode(mode)
    modes = srs.setdefault("modes", {})
    if mode not in modes:
        modes[mode] = _fresh_mode_bucket(card_ids)
    bucket = modes[mode]
    for card_id in card_ids:
        bucket["intervals"].setdefault(card_id, 1)
        bucket.setdefault("ease_factors", {}).setdefault(card_id, 2.5)
        bucket.setdefault("repetitions", {}).setdefault(card_id, 0)
        bucket.setdefault("last_reviewed_at", {}).setdefault(card_id, "")
        bucket["confusion_matrix"].setdefault(card_id, [])
    ensure_schedule(bucket, card_ids)
    return bucket


def deck_srs(store: dict, deck_file: str, cards: list[Card]) -> dict:
    if deck_file not in store["decks"]:
        store["decks"][deck_file] = {"modes": {}}
    srs = store["decks"][deck_file]
    card_ids = [c.id for c in cards]
    migrate_deck_srs(srs, card_ids)
    for mode in DECK_MODES:
        eligible = card_ids
        if mode in ("translate", "translate_reverse"):
            eligible = [c.id for c in cards if c.meaning]
        if eligible:
            mode_schedule(srs, mode, eligible)
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


def remember_mistake(srs: dict, card_id: str, selected: str, *, mode: str) -> None:
    if mode in ("reverse", "translate_reverse"):
        selected = chinese_display(selected)
        if not selected:
            return
    matrix = srs["confusion_matrix"].setdefault(card_id, [])
    if selected not in matrix:
        matrix.append(selected)


def meaning_choice_pool(pool: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in pool:
        if not item or chinese_display(item) or has_pinyin_marks(item):
            continue
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def generate_meaning_choices(correct: str, card_id: str, srs: dict, pool: list[str]) -> list[str]:
    pool = meaning_choice_pool(pool)
    if not correct:
        return pool[:5] if pool else []

    choices = [correct]
    mistakes = srs["confusion_matrix"].get(card_id, []).copy()
    mistakes = list(dict.fromkeys(reversed(mistakes)))
    for mistake in mistakes:
        if chinese_display(mistake) or has_pinyin_marks(mistake):
            continue
        if mistake != correct and mistake not in choices:
            choices.append(mistake)
        if len(choices) == 5:
            break

    if len(choices) < 5:
        answers = [a for a in pool if a not in choices]
        need = 5 - len(choices)
        if answers:
            choices.extend(random.sample(answers, min(need, len(answers))))

    random.shuffle(choices)
    return choices[:5]


def generate_choices(correct: str, card_id: str, srs: dict, pool: list[str]) -> list[str]:
    choices = [correct]
    pool_set = set(pool)
    mistakes = srs["confusion_matrix"].get(card_id, []).copy()
    mistakes = list(dict.fromkeys(reversed(mistakes)))
    for mistake in mistakes:
        if chinese_display(mistake):
            continue
        if mistake not in pool_set and not has_pinyin_marks(mistake):
            continue
        if mistake != correct and mistake not in choices:
            choices.append(mistake)
        if len(choices) == 5:
            break
    if len(choices) < 5:
        answers = [a for a in pool if a and a not in choices]
        need = 5 - len(choices)
        if answers:
            choices.extend(random.sample(answers, min(need, len(answers))))
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

    if len(choices) < 5:
        answers = [a for a in pool if a not in choices]
        need = 5 - len(choices)
        if answers:
            choices.extend(random.sample(answers, min(need, len(answers))))

    random.shuffle(choices)
    return choices[:5]
