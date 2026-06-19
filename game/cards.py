"""Load flashcards from Anki .apkg and plain-text exports."""

from __future__ import annotations

import html
import os
import re
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECKS_DIR = os.path.join(ROOT, "decks")

FIELD_SEP = "\x1f"
SUPPORTED_EXTENSIONS = (".apkg", ".txt")


@dataclass(frozen=True)
class Card:
    id: str
    front: str
    back: str


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _first_line(text: str) -> str:
    line = text.split("\n", 1)[0].strip()
    return line or text.strip()


def decks_dir() -> str:
    os.makedirs(DECKS_DIR, exist_ok=True)
    return DECKS_DIR


def list_deck_files() -> list[str]:
    folder = decks_dir()
    files = [
        name
        for name in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, name))
        and os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files, key=str.lower)


def deck_path(filename: str) -> str:
    return os.path.join(decks_dir(), filename)


def load_deck(filename: str) -> list[Card]:
    path = deck_path(filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Deck not found: {filename}")
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".apkg":
        return load_apkg(path)
    if ext == ".txt":
        return load_anki_txt(path)
    raise ValueError(f"Unsupported deck type: {ext}")


def load_anki_txt(path: str) -> list[Card]:
    cards: list[Card] = []
    with open(path, encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            front = strip_html(parts[0])
            back = strip_html(parts[1])
            if not front or not back:
                continue
            cards.append(Card(id=f"txt-{line_no}", front=front, back=_first_line(back)))
    if not cards:
        raise ValueError("No cards found in text deck")
    return cards


def load_apkg(path: str) -> list[Card]:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if "collection.anki2" not in names:
            if "collection.anki21" in names or "collection.anki21b" in names:
                raise ValueError(
                    "Newer Anki deck format (anki21). Export from Anki as "
                    "'Notes in Plain Text (.txt)' and copy to decks/"
                )
            raise ValueError("No collection.anki2 in .apkg file")

        with zf.open("collection.anki2") as db_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".anki2") as tmp:
                tmp.write(db_file.read())
                tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        try:
            rows = conn.execute("SELECT id, flds FROM notes").fetchall()
        finally:
            conn.close()
    finally:
        os.unlink(tmp_path)

    cards: list[Card] = []
    for note_id, flds in rows:
        fields = flds.split(FIELD_SEP)
        if len(fields) < 2:
            continue
        front = strip_html(fields[0])
        back = strip_html(fields[1])
        if not front or not back:
            continue
        cards.append(Card(id=str(note_id), front=front, back=_first_line(back)))

    if not cards:
        raise ValueError("No usable cards in .apkg (need at least 2 fields per note)")
    return cards
