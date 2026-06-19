"""Bopomofo dictionary and SRS persistence."""

from __future__ import annotations

import json
import os
import random

from game.scheduling import ensure_schedule

BOPOMOFO_DICT = {
    "ㄅ": "b", "ㄆ": "p", "ㄇ": "m", "ㄈ": "f",
    "ㄉ": "d", "ㄊ": "t", "ㄋ": "n", "ㄌ": "l",
    "ㄍ": "g", "ㄎ": "k", "ㄏ": "h",
    "ㄐ": "ji", "ㄑ": "qi", "ㄒ": "xi",
    "ㄓ": "zhi", "ㄔ": "chi", "ㄕ": "shi", "ㄖ": "ri",
    "ㄗ": "zi", "ㄘ": "ci", "ㄙ": "si",
    "ㄚ": "a", "ㄛ": "o", "ㄜ": "e", "ㄝ": "e",
    "ㄞ": "ai", "ㄟ": "ei", "ㄠ": "ao", "ㄡ": "ou",
    "ㄢ": "an", "ㄣ": "en", "ㄤ": "ang", "ㄥ": "eng", "ㄦ": "er",
    "ㄧ": "yi", "ㄨ": "wu", "ㄩ": "yu",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "bopomofo_srs_data.json")


def load_game_data() -> dict:
    default_data = {
        "pack_mode": False,
        "all_time_high_streak": 0,
        "intervals": {char: 1 for char in BOPOMOFO_DICT},
        "confusion_matrix": {char: [] for char in BOPOMOFO_DICT},
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if "all_time_high_streak" in data and "intervals" in data:
                    if "confusion_matrix" not in data:
                        data["confusion_matrix"] = {char: [] for char in BOPOMOFO_DICT}
                    ensure_schedule(data, list(BOPOMOFO_DICT.keys()))
                    return data
        except (OSError, json.JSONDecodeError):
            pass
    ensure_schedule(default_data, list(BOPOMOFO_DICT.keys()))
    return default_data


def save_game_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)


def generate_dynamic_choices(correct_answer: str, char: str, game_data: dict) -> list[str]:
    choices = [correct_answer]

    personal_mistakes = game_data["confusion_matrix"].get(char, []).copy()
    personal_mistakes = list(dict.fromkeys(reversed(personal_mistakes)))

    for mistake in personal_mistakes:
        if mistake != correct_answer and mistake not in choices:
            choices.append(mistake)
        if len(choices) == 5:
            break

    all_pinyins = list(set(BOPOMOFO_DICT.values()))
    while len(choices) < 5:
        rand_pinyin = random.choice(all_pinyins)
        if rand_pinyin not in choices:
            choices.append(rand_pinyin)

    random.shuffle(choices)
    return choices
