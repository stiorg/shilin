#!/usr/bin/env python3
"""Download fonts for Bopomofo, Chinese characters, and pinyin tone marks."""

from __future__ import annotations

import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"

# Traditional Chinese OTF — includes Bopomofo (ㄅㄆㄇ) and Han characters.
TC_URL = (
    "https://github.com/notofonts/noto-cjk/raw/main/"
    "Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
)
TC_FILE = "NotoSansCJKtc-Regular.otf"
# Legacy name used in older README / renderer paths.
TC_ALIAS = "NotoSansTC-Regular.otf"

LATIN_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/"
    "hinted/ttf/NotoSans/NotoSans-Regular.ttf"
)
LATIN_FILE = "NotoSans-Regular.ttf"


def fetch(url: str, dest: pathlib.Path) -> None:
    print(f"Downloading {dest.name} …")
    urllib.request.urlretrieve(url, dest)
    print(f"  -> {dest.stat().st_size:,} bytes")


def main() -> None:
    FONTS.mkdir(exist_ok=True)
    tc_path = FONTS / TC_FILE
    if not tc_path.is_file():
        fetch(TC_URL, tc_path)
    else:
        print(f"Already present: {tc_path.name}")

    alias = FONTS / TC_ALIAS
    if not alias.exists():
        try:
            alias.hardlink_to(tc_path)
            print(f"Linked {TC_ALIAS} -> {TC_FILE}")
        except OSError:
            import shutil

            shutil.copy2(tc_path, alias)
            print(f"Copied {TC_ALIAS}")

    latin_path = FONTS / LATIN_FILE
    if not latin_path.is_file():
        fetch(LATIN_URL, latin_path)
    else:
        print(f"Already present: {latin_path.name}")

    print("Done. Re-run sync-anbernic.bat to push fonts to the handheld.")


if __name__ == "__main__":
    main()
