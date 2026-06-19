"""Character deck study modes."""

from __future__ import annotations

DECK_MODES = ("standard", "reverse", "tone")

DECK_MODE_LABELS = {
    "standard": "Standard",
    "reverse": "Reverse",
    "tone": "Tone",
}

DECK_MODE_DESCRIPTIONS = {
    "standard": "Chinese → Pinyin",
    "reverse": "Pinyin → Chinese",
    "tone": "Train tones",
}


def normalize_mode(mode: str | None) -> str:
    if mode in DECK_MODES:
        return mode
    return "standard"


def cycle_mode(mode: str, delta: int) -> str:
    idx = DECK_MODES.index(normalize_mode(mode))
    return DECK_MODES[(idx + delta) % len(DECK_MODES)]
