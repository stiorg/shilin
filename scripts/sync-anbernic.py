#!/usr/bin/env python3
"""Incremental code sync to Anbernic — only uploads changed files."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import PORT_SLUG

GAME_DIR = f"/mnt/mmc/ports/{PORT_SLUG}"
LAUNCHER = "/mnt/mmc/ROMS/Ports/ShilinTrainer.sh"
SKIP_DIR_NAMES = {"__pycache__", ".git", ".cursor"}
SKIP_SUFFIXES = (".pyc", ".pyo")


@dataclass(frozen=True)
class SyncEntry:
    local: Path
    remote: str
    label: str


def load_credentials(root: Path) -> tuple[str, str]:
    creds_file = root / "credentials.txt"
    if not creds_file.is_file():
        raise FileNotFoundError("credentials.txt not found")
    values: dict[str, str] = {}
    for line in creds_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    user = values.get("DEVICE_USER", "")
    host = values.get("DEVICE_IP", "")
    if not user or not host:
        raise ValueError("credentials.txt must set DEVICE_USER and DEVICE_IP")
    return user, host


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_shell_scripts(root: Path) -> None:
    port = root / "port"
    if not port.is_dir():
        return
    for script in port.glob("*.sh"):
        data = script.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        script.write_bytes(data)


def _should_skip(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def _pick_font(root: Path, *names: str) -> Path | None:
    fonts = root / "fonts"
    for name in names:
        candidate = fonts / name
        if candidate.is_file():
            return candidate
    return None


def collect_entries(root: Path) -> list[SyncEntry]:
    entries: list[SyncEntry] = []

    def add(local_rel: str, remote: str, label: str | None = None) -> None:
        local = root / local_rel
        if local.is_file():
            entries.append(SyncEntry(local, remote, label or local_rel))

    add("main.py", f"{GAME_DIR}/main.py")
    add("requirements.txt", f"{GAME_DIR}/requirements.txt")
    add("port/shilin-trainer.gptk", f"{GAME_DIR}/port/shilin-trainer.gptk")
    add("port/shilin-trainer.sh", LAUNCHER, "ShilinTrainer.sh launcher")

    game_dir = root / "game"
    if game_dir.is_dir():
        for path in sorted(game_dir.rglob("*")):
            if not path.is_file() or _should_skip(path):
                continue
            rel = path.relative_to(root).as_posix()
            entries.append(SyncEntry(path, f"{GAME_DIR}/{rel}", rel))

    decks_dir = root / "decks"
    if decks_dir.is_dir():
        for path in sorted(decks_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            entries.append(SyncEntry(path, f"{GAME_DIR}/{rel}", rel))

    cjk = _pick_font(root, "NotoSansCJKtc-Regular.otf", "NotoSansTC-Regular.otf")
    if cjk:
        entries.append(
            SyncEntry(cjk, f"{GAME_DIR}/fonts/{cjk.name}", f"fonts/{cjk.name}")
        )
    latin = _pick_font(root, "NotoSans-Regular.ttf")
    if latin:
        entries.append(
            SyncEntry(latin, f"{GAME_DIR}/fonts/{latin.name}", f"fonts/{latin.name}")
        )

    return entries


def run_ssh(remote: str, command: str, *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["ssh", remote, command]
    if timeout is not None:
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={timeout}",
            remote,
            command,
        ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def check_connection(remote: str, *, timeout: int = 5) -> None:
    """Fail fast when the handheld is unreachable or credentials are wrong."""
    result = run_ssh(remote, "echo OK", timeout=timeout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "connection failed").strip()
        first_line = detail.splitlines()[0] if detail else "connection failed"
        raise ConnectionError(
            f"Cannot reach {remote} ({first_line}). "
            "Check Wi-Fi, SSH on the device, and DEVICE_IP in credentials.txt "
            "(or pass the new IP: sync-anbernic.bat <ip>)."
        )


def run_scp(local: Path, remote_target: str) -> None:
    result = subprocess.run(
        ["scp", str(local), remote_target],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "scp failed").strip()
        raise RuntimeError(detail)


def remote_digests(remote: str, entries: list[SyncEntry]) -> dict[str, str | None]:
    if not entries:
        return {}
    lines: list[str] = [
        "set -e",
        f"mkdir -p '{GAME_DIR}/port' '{GAME_DIR}/game' '{GAME_DIR}/fonts' '{GAME_DIR}/decks'",
    ]
    for entry in entries:
        path = entry.remote.replace("'", "'\\''")
        lines.append(
            f"if [ -f '{path}' ]; then sha256sum '{path}'; "
            f"else echo 'MISSING {path}'; fi"
        )
    result = run_ssh(remote, "\n".join(lines))
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ssh failed").strip())

    digests: dict[str, str | None] = {entry.remote: None for entry in entries}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("MISSING "):
            digests[line[len("MISSING ") :]] = None
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            digest, path = parts
            digests[path] = digest
    return digests


def pull_progress(remote: str, root: Path) -> None:
    script = root / "scripts" / "sync-progress.py"
    if not script.is_file():
        return
    with tempfile.TemporaryDirectory(prefix="shilin-sync-") as tmp:
        tmp_path = Path(tmp)
        remote_bpm = tmp_path / "bopomofo_srs_data.json"
        remote_fc = tmp_path / "flashcard_srs_data.json"
        for name, dest in (
            ("bopomofo_srs_data.json", remote_bpm),
            ("flashcard_srs_data.json", remote_fc),
        ):
            subprocess.run(
                ["scp", f"{remote}:{GAME_DIR}/{name}", str(dest)],
                capture_output=True,
                check=False,
            )
            if not dest.is_file():
                dest.unlink(missing_ok=True)
        subprocess.run(
            [
                sys.executable,
                str(script),
                "--remote-bpm",
                str(remote_bpm) if remote_bpm.is_file() else "",
                "--remote-fc",
                str(remote_fc) if remote_fc.is_file() else "",
                "--pull-only",
                "--quiet",
            ],
            cwd=root,
            check=True,
        )


def sync_code(remote: str, root: Path, *, force: bool) -> tuple[int, int]:
    entries = collect_entries(root)
    local_hashes = {entry.remote: sha256_file(entry.local) for entry in entries}
    remote_hashes = remote_digests(remote, entries)

    to_upload: list[SyncEntry] = []
    for entry in entries:
        if force or remote_hashes.get(entry.remote) != local_hashes[entry.remote]:
            to_upload.append(entry)

    skipped = len(entries) - len(to_upload)
    for entry in to_upload:
        print(f"  upload {entry.label}")
        run_scp(entry.local, f"{remote}:{entry.remote}")

    if any(entry.remote == LAUNCHER for entry in to_upload):
        run_ssh(remote, f"chmod +x '{LAUNCHER}'")

    if any(entry.remote.startswith(f"{GAME_DIR}/game/") for entry in to_upload):
        run_ssh(
            remote,
            f"find '{GAME_DIR}/game' -type d -name '__pycache__' "
            "-exec rm -rf {} + 2>/dev/null; true",
        )

    return len(to_upload), skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--ip", help="Override DEVICE_IP from credentials.txt")
    parser.add_argument("--force", action="store_true", help="Upload all files")
    parser.add_argument(
        "--skip-progress",
        action="store_true",
        help="Do not pull progress from the device first",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Test SSH connection and exit",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        user, host = load_credentials(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.ip:
        host = args.ip
    remote = f"{user}@{host}"

    if args.check_only:
        try:
            check_connection(remote)
        except ConnectionError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"OK: {remote} is reachable")
        return 0

    print()
    print(f"Syncing code to {remote}")
    print(f"  target   {GAME_DIR}/")
    print(f"  launcher {LAUNCHER}")
    print("  progress never pushed from this script")
    print()

    try:
        check_connection(remote)
    except ConnectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"  connected to {host}")
    print()

    normalize_shell_scripts(root)

    if not args.skip_progress:
        print("[1/2] Pull progress from device (merge into PC only)...")
        try:
            pull_progress(remote, root)
        except subprocess.CalledProcessError as exc:
            print(f"ERROR: progress pull failed: {exc}", file=sys.stderr)
            return 1
        print("      done")
        print()

    print("[2/2] Sync changed files...")
    try:
        uploaded, skipped = sync_code(remote, root, force=args.force)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print()
    print(f"Done. Uploaded {uploaded} file(s), skipped {skipped} unchanged.")
    print("Use sync-progress.bat to sync saves both ways.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
