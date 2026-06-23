"""Mastery score, daily history, and progress graph data."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from game.cards import load_deck, list_deck_files
from game.data import BOPOMOFO_DICT, ROOT
from game.scheduling import (
    DEFAULT_EASE_FACTOR,
    MAX_INTERVAL_DAYS,
    MIN_EASE_FACTOR,
    is_due,
    overdue_days,
    today_str,
)

DAILY_LOG_KEY = "daily_log"
GRAPH_DAYS = 30
LOG_RETENTION_DAYS = 120
_EMPTY_DAY = {"reviews": 0, "correct": 0, "wrong": 0, "score": 0.0, "studied": 0}


def ensure_mastery(game_data: dict) -> None:
    game_data.setdefault(DAILY_LOG_KEY, {})


def _is_studied(bucket: dict, item_id: str) -> bool:
    if bucket.get("last_reviewed_at", {}).get(item_id):
        return True
    if int(bucket.get("repetitions", {}).get(item_id, 0)) > 0:
        return True
    if int(bucket.get("intervals", {}).get(item_id, 1)) > 1:
        return True
    mistakes = bucket.get("confusion_matrix", {}).get(item_id, [])
    return bool(mistakes)


def card_strength(bucket: dict, item_id: str, today: str | None = None) -> float:
    today = today or today_str()
    interval = int(bucket.get("intervals", {}).get(item_id, 1))
    reps = int(bucket.get("repetitions", {}).get(item_id, 0))
    ease = float(bucket.get("ease_factors", {}).get(item_id, DEFAULT_EASE_FACTOR))
    mistakes = len(bucket.get("confusion_matrix", {}).get(item_id, []))

    base = min(interval / MAX_INTERVAL_DAYS, 1.0) * 0.5
    rep_boost = min(reps / 5.0, 1.0) * 0.3
    ease_span = DEFAULT_EASE_FACTOR - MIN_EASE_FACTOR
    ease_boost = max(0.0, (ease - MIN_EASE_FACTOR) / ease_span) * 0.2
    mistake_penalty = min(mistakes * 0.05, 0.25)

    strength = base + rep_boost + ease_boost - mistake_penalty
    strength = max(0.0, min(1.0, strength))
    if is_due(bucket, item_id, today):
        strength *= 0.5
    return strength


def collect_schedule_buckets(game_data: dict, deck_store: dict) -> list[dict]:
    from game.progress_sync import _normalize_bucket, _normalize_deck_entry

    buckets: list[dict] = [_normalize_bucket(game_data)]
    for deck in deck_store.get("decks", {}).values():
        normalized = _normalize_deck_entry(deck)
        for mode_bucket in normalized.get("modes", {}).values():
            if isinstance(mode_bucket, dict):
                buckets.append(mode_bucket)
    return buckets


def mastery_stats(game_data: dict, deck_store: dict, today: str | None = None) -> dict[str, Any]:
    today = today or today_str()
    strengths: list[float] = []
    due_studied = 0
    overdue_sum = 0

    for bucket in collect_schedule_buckets(game_data, deck_store):
        item_ids = set(bucket.get("intervals", {}))
        item_ids.update(bucket.get("last_reviewed_at", {}))
        for item_id in item_ids:
            if not _is_studied(bucket, item_id):
                continue
            strengths.append(card_strength(bucket, item_id, today))
            if is_due(bucket, item_id, today):
                due_studied += 1
                overdue_sum += overdue_days(bucket, item_id, today)

    studied = len(strengths)
    if studied == 0:
        return {
            "score": 0.0,
            "studied": 0,
            "due_studied": 0,
            "available": count_available_cards(deck_store),
        }

    average = sum(strengths) / studied
    due_ratio = due_studied / studied
    overdue_pressure = 0.0
    if due_studied:
        overdue_pressure = min(overdue_sum / due_studied / 30.0, 1.0)
    penalty = 0.35 * due_ratio + 0.15 * overdue_pressure
    score = max(0.0, min(100.0, (average - penalty) * 100.0))

    return {
        "score": round(score, 1),
        "studied": studied,
        "due_studied": due_studied,
        "available": count_available_cards(deck_store),
    }


_available_count_cache: tuple[frozenset[str], int] | None = None


def count_available_cards(deck_store: dict) -> int:
    global _available_count_cache
    deck_names = frozenset(deck_store.get("decks", {})) | frozenset(list_deck_files())
    if _available_count_cache is not None:
        cached_names, cached_total = _available_count_cache
        if cached_names == deck_names:
            return cached_total

    total = len(BOPOMOFO_DICT)
    decks_dir = os.path.join(ROOT, "decks")
    for deck_file in deck_names:
        path = os.path.join(decks_dir, deck_file)
        if not os.path.isfile(path):
            continue
        try:
            total += len(load_deck(deck_file))
        except (OSError, ValueError):
            continue
    _available_count_cache = (deck_names, total)
    return total


def invalidate_available_cache() -> None:
    global _available_count_cache
    _available_count_cache = None


def _today_entry(game_data: dict) -> dict:
    ensure_mastery(game_data)
    log = game_data[DAILY_LOG_KEY]
    day = today_str()
    if day not in log:
        log[day] = dict(_EMPTY_DAY)
    return log[day]


def record_review(game_data: dict, correct: bool) -> None:
    entry = _today_entry(game_data)
    entry["reviews"] = int(entry.get("reviews", 0)) + 1
    if correct:
        entry["correct"] = int(entry.get("correct", 0)) + 1
    else:
        entry["wrong"] = int(entry.get("wrong", 0)) + 1


def snapshot_mastery(
    game_data: dict, deck_store: dict, stats: dict[str, Any] | None = None
) -> float:
    ensure_mastery(game_data)
    if stats is None:
        stats = mastery_stats(game_data, deck_store)
    entry = _today_entry(game_data)
    entry["score"] = stats["score"]
    entry["studied"] = stats["studied"]
    _trim_log(game_data)
    return stats["score"]


def _trim_log(game_data: dict) -> None:
    log = game_data.get(DAILY_LOG_KEY, {})
    if not log:
        return
    cutoff = date.today() - timedelta(days=LOG_RETENTION_DAYS)
    for day in list(log):
        try:
            if parse_day(day) < cutoff:
                del log[day]
        except ValueError:
            del log[day]


def parse_day(day: str) -> date:
    return date.fromisoformat(day)


def graph_series(game_data: dict, days: int = GRAPH_DAYS) -> list[tuple[str, float]]:
    ensure_mastery(game_data)
    log = game_data.get(DAILY_LOG_KEY, {})
    today = date.today()
    series: list[tuple[str, float]] = []
    last_score = 0.0
    had_data = False
    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        entry = log.get(day)
        if entry and (
            int(entry.get("reviews", 0)) > 0
            or float(entry.get("score", 0)) > 0
            or int(entry.get("studied", 0)) > 0
        ):
            last_score = float(entry.get("score", last_score))
            had_data = True
        series.append((day[5:], last_score if had_data else 0.0))
    return series


def merge_daily_log(local: dict, remote: dict) -> dict:
    merged: dict[str, dict] = {}
    for day in set(local) | set(remote):
        a = local.get(day, {})
        b = remote.get(day, {})
        if not a and not b:
            continue
        merged[day] = {
            "reviews": int(a.get("reviews", 0)) + int(b.get("reviews", 0)),
            "correct": int(a.get("correct", 0)) + int(b.get("correct", 0)),
            "wrong": int(a.get("wrong", 0)) + int(b.get("wrong", 0)),
            "score": max(float(a.get("score", 0)), float(b.get("score", 0))),
            "studied": max(int(a.get("studied", 0)), int(b.get("studied", 0))),
        }
    return merged


def format_score_line(game_data: dict, deck_store: dict, stats: dict[str, Any] | None = None) -> str:
    if stats is None:
        stats = mastery_stats(game_data, deck_store)
    if stats["studied"] == 0:
        return f"Mastery: -  |  {stats['available']} cards to learn"
    return (
        f"Mastery: {stats['score']:.0f}%"
        f"  |  {stats['studied']} studied"
        f"  |  {stats['available']} available"
    )
