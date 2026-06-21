#!/usr/bin/env python3
"""Merge local and remote SRS progress (card-level, latest review wins)."""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from game.config import PORT_SLUG
from game.data import BOPOMOFO_DICT, DATA_FILE as BOPOMOFO_FILE
from game.deck_store import DATA_FILE as FLASHCARD_FILE
from game.progress_sync import (
    default_bopomofo_data,
    default_flashcard_store,
    load_json_file,
    merge_bopomofo,
    merge_flashcard_store,
)

DEFAULT_REMOTE_DIR = f"/mnt/mmc/ports/{PORT_SLUG}"


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)


def run_merge(
    root: str,
    remote_bpm: str | None,
    remote_fc: str | None,
    *,
    pull_only: bool = False,
    quiet: bool = False,
) -> int:
    local_bpm_path = os.path.join(root, BOPOMOFO_FILE)
    local_fc_path = os.path.join(root, FLASHCARD_FILE)
    item_ids = list(BOPOMOFO_DICT.keys())

    local_bpm = load_json_file(local_bpm_path, default_bopomofo_data(item_ids))
    remote_bpm = load_json_file(remote_bpm or "", default_bopomofo_data(item_ids))
    merged_bpm, bpm_stats = merge_bopomofo(local_bpm, remote_bpm, item_ids)

    local_fc = load_json_file(local_fc_path, default_flashcard_store())
    remote_fc = load_json_file(remote_fc or "", default_flashcard_store())
    merged_fc, fc_stats = merge_flashcard_store(local_fc, remote_fc)

    _write_json(local_bpm_path, merged_bpm)
    _write_json(local_fc_path, merged_fc)

    if not quiet:
        print()
        print("Bopomofo progress:")
        for line in bpm_stats.report_lines():
            print(line)
        print()
        print("Character deck progress:")
        for line in fc_stats.report_lines():
            print(line)
        print()
        print(f"Wrote {BOPOMOFO_FILE}")
        print(f"Wrote {FLASHCARD_FILE}")
        if pull_only:
            print("Pull only — device save files were not modified.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=ROOT,
        help="Project root containing save JSON files (default: repo root)",
    )
    parser.add_argument(
        "--remote-bpm",
        help="Path to bopomofo_srs_data.json fetched from the handheld",
    )
    parser.add_argument(
        "--remote-fc",
        help="Path to flashcard_srs_data.json fetched from the handheld",
    )
    parser.add_argument(
        "--pull-only",
        action="store_true",
        help="Merge into local files only; never push saves to the device",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors",
    )
    args = parser.parse_args()
    return run_merge(
        args.root,
        args.remote_bpm,
        args.remote_fc,
        pull_only=args.pull_only,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    raise SystemExit(main())
