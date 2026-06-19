"""Calendar-based spaced repetition (Anki-style due dates)."""

from __future__ import annotations

import random
from datetime import date, timedelta

MAX_INTERVAL_DAYS = 180


def today_str() -> str:
    return date.today().isoformat()


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def add_days(day: str, days: int) -> str:
    return (parse_day(day) + timedelta(days=days)).isoformat()


def ensure_schedule(srs: dict, item_ids: list[str]) -> None:
    """Ensure due dates exist; migrate legacy interval-only data."""
    intervals = srs.setdefault("intervals", {})
    due = srs.setdefault("due", {})
    today = today_str()
    for item_id in item_ids:
        intervals.setdefault(item_id, 1)
        if item_id not in due:
            # Legacy intervals were review weights, not calendar spacing.
            # Treat unseen due entries as due today so scheduling starts cleanly.
            due[item_id] = today


def interval_days(srs: dict, item_id: str) -> int:
    return int(srs["intervals"].get(item_id, 1))


def due_on(srs: dict, item_id: str) -> str:
    return srs["due"].get(item_id, today_str())


def is_due(srs: dict, item_id: str, today: str | None = None) -> bool:
    today = today or today_str()
    return due_on(srs, item_id) <= today


def overdue_days(srs: dict, item_id: str, today: str | None = None) -> int:
    today = today or today_str()
    return max(0, (parse_day(today) - parse_day(due_on(srs, item_id))).days)


def due_ids(srs: dict, item_ids: list[str], today: str | None = None) -> list[str]:
    today = today or today_str()
    return [item_id for item_id in item_ids if is_due(srs, item_id, today)]


def due_count(srs: dict, item_ids: list[str], today: str | None = None) -> int:
    return len(due_ids(srs, item_ids, today))


def sorted_due_ids(srs: dict, item_ids: list[str], today: str | None = None) -> list[str]:
    """Most overdue first, then shorter intervals."""
    today = today or today_str()

    def sort_key(item_id: str) -> tuple[int, int, str]:
        return (-overdue_days(srs, item_id, today), interval_days(srs, item_id), item_id)

    return sorted(due_ids(srs, item_ids, today), key=sort_key)


def pick_due_id(srs: dict, item_ids: list[str], today: str | None = None) -> str | None:
    today = today or today_str()
    due = due_ids(srs, item_ids, today)
    if not due:
        return None
    weights = [1 + overdue_days(srs, item_id, today) for item_id in due]
    return random.choices(due, weights=weights, k=1)[0]


def schedule_correct(srs: dict, item_id: str, today: str | None = None) -> int:
    today = today or today_str()
    interval = interval_days(srs, item_id)
    new_interval = min(max(interval * 2, 1), MAX_INTERVAL_DAYS)
    srs["intervals"][item_id] = new_interval
    srs["due"][item_id] = add_days(today, new_interval)
    return new_interval


def schedule_wrong(srs: dict, item_id: str, today: str | None = None) -> None:
    today = today or today_str()
    srs["intervals"][item_id] = 1
    srs["due"][item_id] = today


def due_menu_suffix(count: int) -> str:
    if count <= 0:
        return " (caught up)"
    if count == 1:
        return " (1 due)"
    return f" ({count} due)"
