"""Calendar-based spaced repetition using the SuperMemo SM-2 algorithm."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

MAX_INTERVAL_DAYS = 180
DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
QUALITY_CORRECT = 4
QUALITY_WRONG = 1


def today_str() -> str:
    return date.today().isoformat()


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def add_days(day: str, days: int) -> str:
    return (parse_day(day) + timedelta(days=days)).isoformat()


def _infer_repetitions(interval: int) -> int:
    """Best-effort SM-2 repetition count when migrating legacy interval data."""
    if interval <= 1:
        return 0
    if interval <= 6:
        return 1
    return 2


def _update_ease_factor(ease_factor: float, quality: int) -> float:
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    return max(MIN_EASE_FACTOR, ease_factor + delta)


def review_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_schedule(srs: dict, item_ids: list[str]) -> None:
    """Ensure due dates and SM-2 fields exist; migrate legacy interval-only data."""
    intervals = srs.setdefault("intervals", {})
    due = srs.setdefault("due", {})
    ease_factors = srs.setdefault("ease_factors", {})
    repetitions = srs.setdefault("repetitions", {})
    last_reviewed = srs.setdefault("last_reviewed_at", {})
    today = today_str()
    for item_id in item_ids:
        intervals.setdefault(item_id, 1)
        ease_factors.setdefault(item_id, DEFAULT_EASE_FACTOR)
        repetitions.setdefault(item_id, _infer_repetitions(intervals[item_id]))
        last_reviewed.setdefault(item_id, "")
        if item_id not in due:
            # Legacy intervals were review weights, not calendar spacing.
            # Treat unseen due entries as due today so scheduling starts cleanly.
            due[item_id] = today


def interval_days(srs: dict, item_id: str) -> int:
    return int(srs["intervals"].get(item_id, 1))


def ease_factor(srs: dict, item_id: str) -> float:
    return float(srs.setdefault("ease_factors", {}).get(item_id, DEFAULT_EASE_FACTOR))


def repetition_count(srs: dict, item_id: str) -> int:
    return int(srs.setdefault("repetitions", {}).get(item_id, 0))


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
    """Most overdue first, then shorter intervals; shuffle within equal priority."""
    today = today or today_str()

    def sort_key(item_id: str) -> tuple[int, int]:
        return (-overdue_days(srs, item_id, today), interval_days(srs, item_id))

    keyed = sorted(
        ((sort_key(item_id), item_id) for item_id in due_ids(srs, item_ids, today)),
        key=lambda pair: pair[0],
    )
    result: list[str] = []
    index = 0
    while index < len(keyed):
        key = keyed[index][0]
        group: list[str] = []
        while index < len(keyed) and keyed[index][0] == key:
            group.append(keyed[index][1])
            index += 1
        random.shuffle(group)
        result.extend(group)
    return result


def pick_due_id(srs: dict, item_ids: list[str], today: str | None = None) -> str | None:
    today = today or today_str()
    due = due_ids(srs, item_ids, today)
    if not due:
        return None
    weights = [1 + overdue_days(srs, item_id, today) for item_id in due]
    return random.choices(due, weights=weights, k=1)[0]


def sm2_schedule(
    srs: dict,
    item_id: str,
    quality: int,
    today: str | None = None,
) -> int:
    """Apply SuperMemo SM-2 for a review quality in 0..5. Returns new interval days."""
    today = today or today_str()
    quality = max(0, min(5, quality))
    ef = ease_factor(srs, item_id)
    reps = repetition_count(srs, item_id)
    interval = interval_days(srs, item_id)

    if quality < 3:
        reps = 0
        new_interval = 1
    else:
        ef = _update_ease_factor(ef, quality)
        if reps == 0:
            new_interval = 1
        elif reps == 1:
            new_interval = 6
        else:
            new_interval = max(1, round(interval * ef))
        reps += 1

    new_interval = min(new_interval, MAX_INTERVAL_DAYS)
    srs.setdefault("ease_factors", {})[item_id] = ef
    srs.setdefault("repetitions", {})[item_id] = reps
    srs["intervals"][item_id] = new_interval
    if quality < 3:
        # Keep failed cards in today's queue for same-session re-review.
        srs["due"][item_id] = today
    else:
        srs["due"][item_id] = add_days(today, new_interval)
    srs.setdefault("last_reviewed_at", {})[item_id] = review_timestamp()
    return new_interval


def schedule_correct(srs: dict, item_id: str, today: str | None = None) -> int:
    return sm2_schedule(srs, item_id, QUALITY_CORRECT, today)


def schedule_wrong(srs: dict, item_id: str, today: str | None = None) -> None:
    sm2_schedule(srs, item_id, QUALITY_WRONG, today)


def due_menu_suffix(count: int) -> str:
    if count <= 0:
        return " (caught up)"
    if count == 1:
        return " (1 due)"
    return f" ({count} due)"
