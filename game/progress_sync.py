"""Merge SRS progress between devices at card level (latest review wins)."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from game.mastery import DAILY_LOG_KEY, merge_daily_log
from game.scheduling import ensure_schedule, parse_day

Side = Literal["local", "remote"]
SCHEDULE_ITEM_FIELDS = ("intervals", "ease_factors", "repetitions", "due", "last_reviewed_at")
SCHEDULE_DICT_FIELDS = SCHEDULE_ITEM_FIELDS + ("confusion_matrix",)


@dataclass
class MergeStats:
    local_wins: int = 0
    remote_wins: int = 0
    legacy_ties: int = 0
    decks_merged: int = 0
    modes_merged: int = 0

    def report_lines(self) -> list[str]:
        return [
            f"  cards kept from PC: {self.local_wins}",
            f"  cards kept from device: {self.remote_wins}",
            f"  cards without timestamps (progress tie-break): {self.legacy_ties}",
            f"  deck buckets merged: {self.decks_merged}",
        ]


def parse_review_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _item_ids(*buckets: dict) -> set[str]:
    ids: set[str] = set()
    for bucket in buckets:
        for field_name in SCHEDULE_DICT_FIELDS:
            ids.update(bucket.get(field_name, {}))
    return ids


def _normalize_bucket(bucket: dict) -> dict:
    """Ensure schedule buckets have all expected dict fields (legacy saves may omit some)."""
    normalized: dict[str, Any] = {
        "all_time_high_streak": int(bucket.get("all_time_high_streak", 0)),
    }
    for field_name in SCHEDULE_DICT_FIELDS:
        value = bucket.get(field_name, {})
        normalized[field_name] = dict(value) if isinstance(value, dict) else {}
    return normalized


def _normalize_deck_entry(deck: dict) -> dict:
    """Support legacy deck saves that stored SRS fields at the deck root."""
    if "modes" in deck:
        modes = deck.get("modes", {})
        return {
            "modes": {
                mode_name: _normalize_bucket(bucket)
                for mode_name, bucket in modes.items()
                if isinstance(bucket, dict)
            }
        }
    if "intervals" in deck:
        legacy_bucket = _normalize_bucket(deck)
        return {"modes": {"standard": legacy_bucket}}
    return {"modes": {}}


def _legacy_progress_key(bucket: dict, item_id: str) -> tuple:
    due_raw = bucket.get("due", {}).get(item_id, "")
    try:
        due_day = parse_day(due_raw) if due_raw else parse_day("1970-01-01")
    except ValueError:
        due_day = parse_day("1970-01-01")
    interval = int(bucket.get("intervals", {}).get(item_id, 1))
    reps = int(bucket.get("repetitions", {}).get(item_id, 0))
    return (due_day, interval, reps)


def pick_item_side(local: dict, remote: dict, item_id: str) -> tuple[Side, bool]:
    """Return winning side and whether the decision used legacy fallback."""
    local_ts = parse_review_time(local.get("last_reviewed_at", {}).get(item_id, ""))
    remote_ts = parse_review_time(remote.get("last_reviewed_at", {}).get(item_id, ""))
    if local_ts and remote_ts:
        return ("local", False) if local_ts >= remote_ts else ("remote", False)
    if local_ts:
        return "local", False
    if remote_ts:
        return "remote", False

    local_key = _legacy_progress_key(local, item_id)
    remote_key = _legacy_progress_key(remote, item_id)
    if local_key >= remote_key:
        return "local", True
    return "remote", True


def _copy_item_fields(source: dict, dest: dict, item_id: str) -> None:
    for field_name in SCHEDULE_ITEM_FIELDS:
        bucket = source.get(field_name, {})
        if item_id in bucket:
            dest.setdefault(field_name, {})[item_id] = bucket[item_id]


def merge_confusion_matrix(local: list[str], remote: list[str], winner: Side) -> list[str]:
    first = local if winner == "local" else remote
    second = remote if winner == "local" else local
    seen: set[str] = set()
    merged: list[str] = []
    for mistake in first + second:
        if mistake not in seen:
            seen.add(mistake)
            merged.append(mistake)
    return merged


def merge_schedule_bucket(local: dict, remote: dict, stats: MergeStats) -> dict:
    local = _normalize_bucket(local)
    remote = _normalize_bucket(remote)
    merged: dict[str, Any] = {}
    for item_id in _item_ids(local, remote):
        winner, legacy = pick_item_side(local, remote, item_id)
        source = local if winner == "local" else remote
        _copy_item_fields(source, merged, item_id)
        local_mistakes = local.get("confusion_matrix", {}).get(item_id, [])
        remote_mistakes = remote.get("confusion_matrix", {}).get(item_id, [])
        merged.setdefault("confusion_matrix", {})[item_id] = merge_confusion_matrix(
            local_mistakes,
            remote_mistakes,
            winner,
        )
        if legacy:
            stats.legacy_ties += 1
        elif winner == "local":
            stats.local_wins += 1
        else:
            stats.remote_wins += 1

    merged["all_time_high_streak"] = max(
        int(local.get("all_time_high_streak", 0)),
        int(remote.get("all_time_high_streak", 0)),
    )
    return merged


def newest_review_time(bucket: dict) -> datetime | None:
    best: datetime | None = None
    for raw in bucket.get("last_reviewed_at", {}).values():
        ts = parse_review_time(raw)
        if ts and (best is None or ts > best):
            best = ts
    return best


def newest_review_time_in_store(store: dict) -> datetime | None:
    best: datetime | None = None
    top = newest_review_time(store)
    if top and (best is None or top > best):
        best = top
    for deck in store.get("decks", {}).values():
        for bucket in deck.get("modes", {}).values():
            ts = newest_review_time(bucket)
            if ts and (best is None or ts > best):
                best = ts
    return best


def pick_settings_side(local: dict, remote: dict) -> Side:
    local_ts = newest_review_time(local)
    remote_ts = newest_review_time(remote)
    if local_ts and remote_ts:
        return "local" if local_ts >= remote_ts else "remote"
    if local_ts:
        return "local"
    if remote_ts:
        return "remote"
    return "local"


def pick_store_settings_side(local: dict, remote: dict) -> Side:
    local_ts = newest_review_time_in_store(local)
    remote_ts = newest_review_time_in_store(remote)
    if local_ts and remote_ts:
        return "local" if local_ts >= remote_ts else "remote"
    if local_ts:
        return "local"
    if remote_ts:
        return "remote"
    return "local"


def merge_bopomofo(local: dict, remote: dict, item_ids: list[str]) -> tuple[dict, MergeStats]:
    stats = MergeStats()
    ensure_schedule(local, item_ids)
    ensure_schedule(remote, item_ids)
    merged = merge_schedule_bucket(local, remote, stats)
    settings_side = pick_settings_side(local, remote)
    source = local if settings_side == "local" else remote
    merged["pack_mode"] = bool(source.get("pack_mode", False))
    merged["all_time_high_streak"] = max(
        int(local.get("all_time_high_streak", 0)),
        int(remote.get("all_time_high_streak", 0)),
        int(merged.get("all_time_high_streak", 0)),
    )
    merged[DAILY_LOG_KEY] = merge_daily_log(
        local.get(DAILY_LOG_KEY, {}),
        remote.get(DAILY_LOG_KEY, {}),
    )
    return merged, stats


def merge_flashcard_store(local: dict, remote: dict) -> tuple[dict, MergeStats]:
    stats = MergeStats()
    merged = copy.deepcopy(local)
    merged.setdefault("decks", {})

    deck_names = set(local.get("decks", {})) | set(remote.get("decks", {}))
    for deck_name in deck_names:
        local_deck = _normalize_deck_entry(local.get("decks", {}).get(deck_name, {}))
        remote_deck = _normalize_deck_entry(remote.get("decks", {}).get(deck_name, {}))
        local_modes = local_deck.get("modes", {})
        remote_modes = remote_deck.get("modes", {})
        mode_names = set(local_modes) | set(remote_modes)
        if not mode_names:
            continue

        merged_deck = merged["decks"].setdefault(deck_name, {"modes": {}})
        merged_modes = merged_deck.setdefault("modes", {})
        for mode_name in mode_names:
            local_bucket = local_modes.get(mode_name, {})
            remote_bucket = remote_modes.get(mode_name, {})
            merged_modes[mode_name] = merge_schedule_bucket(
                local_bucket,
                remote_bucket,
                stats,
            )
            stats.modes_merged += 1
        stats.decks_merged += 1

    settings_side = pick_store_settings_side(local, remote)
    source = local if settings_side == "local" else remote
    merged["last_deck"] = source.get("last_deck", "")
    merged["deck_mode"] = source.get("deck_mode", "standard")
    merged["pack_mode"] = bool(source.get("pack_mode", False))
    merged["all_time_high_streak"] = max(
        int(local.get("all_time_high_streak", 0)),
        int(remote.get("all_time_high_streak", 0)),
    )
    return merged, stats


def load_json_file(path: str, default: dict) -> dict:
    if not path or not os.path.isfile(path):
        return copy.deepcopy(default)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return copy.deepcopy(default)


def default_bopomofo_data(item_ids: list[str]) -> dict:
    return {
        "pack_mode": False,
        "all_time_high_streak": 0,
        "intervals": {item_id: 1 for item_id in item_ids},
        "ease_factors": {item_id: 2.5 for item_id in item_ids},
        "repetitions": {item_id: 0 for item_id in item_ids},
        "last_reviewed_at": {item_id: "" for item_id in item_ids},
        "confusion_matrix": {item_id: [] for item_id in item_ids},
        "daily_log": {},
    }


def default_flashcard_store() -> dict:
    return {
        "last_deck": "",
        "deck_mode": "standard",
        "pack_mode": False,
        "decks": {},
    }
