"""Character deck study modes."""

from __future__ import annotations

DECK_MODES = ("standard", "reverse", "tone", "translate", "translate_reverse")

DECK_MODE_LABELS = {
    "standard": "Standard",
    "reverse": "Reverse",
    "tone": "Tone",
    "translate": "Translate",
    "translate_reverse": "Translate Rev",
}

DECK_MODE_DESCRIPTIONS = {
    "standard": "Chinese → Pinyin",
    "reverse": "Pinyin → Chinese",
    "tone": "Train tones",
    "translate": "Chinese → Meaning",
    "translate_reverse": "Meaning → Chinese",
}


def normalize_mode(mode: str | None) -> str:
    if mode in DECK_MODES:
        return mode
    return "standard"


def cycle_mode(mode: str, delta: int) -> str:
    idx = DECK_MODES.index(normalize_mode(mode))
    return DECK_MODES[(idx + delta) % len(DECK_MODES)]


def is_tone_mode(mode: str) -> bool:
    return mode == "tone"


def requires_meaning(mode: str) -> bool:
    return mode in ("translate", "translate_reverse")


def uses_chinese_choices(mode: str) -> bool:
    return mode in ("reverse", "translate_reverse")


def uses_pinyin_prompt(mode: str) -> bool:
    return mode == "reverse"


def uses_latin_prompt(mode: str) -> bool:
    return mode == "translate_reverse"
