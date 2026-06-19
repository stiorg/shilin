"""Pinyin tone helpers for character tone-training mode."""

from __future__ import annotations

_TONE_MARKS: dict[str, tuple[str, int]] = {
    "ā": ("a", 1),
    "á": ("a", 2),
    "ǎ": ("a", 3),
    "à": ("a", 4),
    "ē": ("e", 1),
    "é": ("e", 2),
    "ě": ("e", 3),
    "è": ("e", 4),
    "ī": ("i", 1),
    "í": ("i", 2),
    "ǐ": ("i", 3),
    "ì": ("i", 4),
    "ō": ("o", 1),
    "ó": ("o", 2),
    "ǒ": ("o", 3),
    "ò": ("o", 4),
    "ū": ("u", 1),
    "ú": ("u", 2),
    "ǔ": ("u", 3),
    "ù": ("u", 4),
    "ǖ": ("ü", 1),
    "ǘ": ("ü", 2),
    "ǚ": ("ü", 3),
    "ǜ": ("ü", 4),
    "Ā": ("A", 1),
    "Á": ("A", 2),
    "Ǎ": ("A", 3),
    "À": ("A", 4),
    "Ē": ("E", 1),
    "É": ("E", 2),
    "Ě": ("E", 3),
    "È": ("E", 4),
    "Ī": ("I", 1),
    "Í": ("I", 2),
    "Ǐ": ("I", 3),
    "Ì": ("I", 4),
    "Ō": ("O", 1),
    "Ó": ("O", 2),
    "Ǒ": ("O", 3),
    "Ò": ("O", 4),
    "Ū": ("U", 1),
    "Ú": ("U", 2),
    "Ǔ": ("U", 3),
    "Ù": ("U", 4),
}

_TONE_TO_MARK: dict[tuple[str, int], str] = {
    (base, tone): mark for mark, (base, tone) in _TONE_MARKS.items()
}
_VOWEL_BASES = "aeiouüAEIOUÜ"


def strip_tones(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch in _TONE_MARKS:
            out.append(_TONE_MARKS[ch][0])
        else:
            out.append(ch)
    return "".join(out)


def _tone_vowel_index(syllable: str) -> int | None:
    lower = syllable.lower().replace("v", "ü")
    if "a" in lower:
        return lower.rindex("a")
    if "e" in lower:
        return lower.rindex("e")
    if "ou" in lower:
        return lower.rindex("o")
    for idx in range(len(syllable) - 1, -1, -1):
        if syllable[idx] in _VOWEL_BASES:
            return idx
    return None


def _apply_tone(syllable: str, tone: int) -> str:
    if tone == 5:
        return strip_tones(syllable)
    idx = _tone_vowel_index(syllable)
    if idx is None:
        return syllable
    base = syllable[idx]
    base_key = base.lower()
    if base_key == "v":
        base_key = "ü"
    mark = _TONE_TO_MARK.get((base_key, tone))
    if mark is None:
        return syllable
    if base.isupper() and base_key != "ü":
        mark = mark.upper()
    return syllable[:idx] + mark + syllable[idx + 1 :]


def build_reading(syllables: list[str], tones: list[int]) -> str:
    return " ".join(_apply_tone(syl, tone) for syl, tone in zip(syllables, tones))


def syllable_tone(syllable: str) -> int:
    for ch in syllable:
        if ch in _TONE_MARKS:
            return _TONE_MARKS[ch][1]
    return 5


def parse_reading(reading: str) -> list[str]:
    return [strip_tones(part) for part in reading.split()]


def cycle_tone(tone: int, delta: int) -> int:
    order = (1, 2, 3, 4, 5)
    idx = order.index(tone) if tone in order else 4
    return order[(idx + delta) % len(order)]


def needs_cjk_font(text: str) -> bool:
    return any(is_cjk_script_char(ch) for ch in text)


def is_cjk_script_char(ch: str) -> bool:
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF
        or 0x3100 <= o <= 0x312F
        or 0x31A0 <= o <= 0x31BF
    )


def has_pinyin_marks(text: str) -> bool:
    return any(ch in _TONE_MARKS for ch in text)
