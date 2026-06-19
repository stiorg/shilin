"""Build TOCFL deck files under decks/ (tocfl1a.txt, tocfl1b.txt, …).

Source: ivankra/tocfl top-20111208.csv (SC-TOP 8000-word list, 2011 edition).
Each L1–L4 bucket becomes one deck; the old level-5 bucket is split into 3a/3b
because that export predates the separate Level 5 / Level 6 lists.

Run: python scripts/build-tocfl-deck.py
"""

from __future__ import annotations

import csv
import io
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECKS_DIR = os.path.join(ROOT, "decks")
SOURCE_URL = (
    "https://raw.githubusercontent.com/ivankra/tocfl/master/top-20111208.csv"
)

_TONE_TO_BASE = {
    "ā": "a",
    "á": "a",
    "ǎ": "a",
    "à": "a",
    "ē": "e",
    "é": "e",
    "ě": "e",
    "è": "e",
    "ī": "i",
    "í": "i",
    "ǐ": "i",
    "ì": "i",
    "ō": "o",
    "ó": "o",
    "ǒ": "o",
    "ò": "o",
    "ū": "u",
    "ú": "u",
    "ǔ": "u",
    "ù": "u",
    "ǖ": "v",
    "ǘ": "v",
    "ǚ": "v",
    "ǜ": "v",
    "ü": "v",
}

_VALID_SYLLABLES = frozenset(
    """
    a ai an ang ao ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu
    ca cai can cang cao ce cen ceng cha chai chan chang chao che chen cheng chi chong
    chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu cuan cui cun cuo
    da dai dan dang dao de dei den deng di dian diao die ding diu dong dou du duan dui
    dun duo e en eng er fa fan fang fei fen feng fo fou fu ga gai gan gang gao ge gei
    gen geng gong gou gu gua guai guan guang gui gun guo ha hai han hang hao he hei hen
    heng hong hou hu hua huai huan huang hui hun huo ji jia jian jiang jiao jie jin jing
    jiong jiu ju juan jue jun ka kai kan kang kao ke ken keng kong kou ku kua kuai kuan
    kuang kui kun kuo la lai lan lang lao le lei leng li lia lian liang liao lie lin ling
    liu long lou lu luan lue lun luo lv lve ma mai man mang mao me mei men meng mi mian
    miao mie min ming miu mo mou mu na nai nan nang nao ne nei nen neng ni nian niang
    niao nie nin ning niu nong nou nu nuan nue nun nuo nv nve o ou pa pai pan pang pao
    pei pen peng pi pian piao pie pin ping po pou pu qi qia qian qiang qiao qie qin qing
    qiong qiu qu quan que qun ran rang rao re ren reng ri rong rou ru rua ruan rui run
    ruo sa sai san sang sao se sen seng sha shai shan shang shao she shen sheng shi shou
    shu shua shuai shuan shuang shui shun shuo si song sou su suan sui sun suo ta tai tan
    tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun tuo wa wai wan wang
    wei wen weng wo wu xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun ya
    yan yang yao ye yi yin ying yo yong you yu yuan yue yun za zai zan zang zao ze zei
    zen zeng zha zhai zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua zhuai
    zhuan zhuang zhui zhun zhuo zi zong zou zu zuan zui zun zuo
    """.split()
)

_HEADER_LINES = 5

# deck suffix -> (csv level prefix, title line)
LEVELS: dict[str, tuple[str, str]] = {
    "1a": ("L1", "TOCFL Band A · Level 1 · 入門級 (A1)"),
    "1b": ("L2", "TOCFL Band A · Level 2 · 基礎級 (A2)"),
    "2a": ("L3", "TOCFL Band B · Level 3 · 進階級 (B1)"),
    "2b": ("L4", "TOCFL Band B · Level 4 · 高階級 (B2)"),
    "3a": (
        "L5a",
        "TOCFL Band C · Level 5 · 流利級 (C1) — first half of SC-TOP level-5 list",
    ),
    "3b": (
        "L5b",
        "TOCFL Band C · Level 6 · 精通級 (C2) — second half of SC-TOP level-5 list",
    ),
}


def _plain_pinyin(text: str) -> str:
    return "".join(_TONE_TO_BASE.get(ch, ch) for ch in text.lower())


def _split_part(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    plain = _plain_pinyin(text)
    pos = 0
    chunks: list[str] = []
    while pos < len(plain):
        matched_len = 0
        for size in range(min(6, len(plain) - pos), 0, -1):
            if plain[pos : pos + size] in _VALID_SYLLABLES:
                matched_len = size
                break
        if matched_len == 0:
            matched_len = 1
        chunks.append(text[pos : pos + matched_len])
        pos += matched_len
    return chunks


def space_pinyin(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    text = re.sub(r"[()（）]", " ", text)
    parts = re.split(r"[\s/]+", text)
    syllables: list[str] = []
    for part in parts:
        if part:
            syllables.extend(_split_part(part))
    return " ".join(syllables)


def pick_traditional(text: str) -> str:
    if "/" not in text:
        return text
    parts = text.split("/")
    for part in parts:
        if "臺" in part:
            return part
    return parts[0]


def clean_meaning(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text.replace("\t", " ")


def _rows_by_level(raw: str) -> dict[str, list[dict[str, str]]]:
    rows = list(csv.DictReader(io.StringIO(raw)))
    grouped: dict[str, list[dict[str, str]]] = {key: [] for key in LEVELS}
    l5_rows: list[dict[str, str]] = []
    for row in rows:
        level_id = row["ID"]
        if level_id.startswith("L1-"):
            grouped["1a"].append(row)
        elif level_id.startswith("L2-"):
            grouped["1b"].append(row)
        elif level_id.startswith("L3-"):
            grouped["2a"].append(row)
        elif level_id.startswith("L4-"):
            grouped["2b"].append(row)
        elif level_id.startswith("L5-"):
            l5_rows.append(row)
    mid = len(l5_rows) // 2
    grouped["3a"] = l5_rows[:mid]
    grouped["3b"] = l5_rows[mid:]
    return grouped


def _deck_lines(title: str, rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "#separator:tab",
        "#html:false",
        f"# {title}",
        "# Regenerate: python scripts/build-tocfl-deck.py",
        "# field 1 = character, field 2 = pinyin, field 3 = English meaning",
    ]
    for row in rows:
        front = pick_traditional(row["Traditional"].strip())
        back = space_pinyin(row["Pinyin"].strip())
        meaning = clean_meaning(row.get("Meaning", ""))
        if not front or not back:
            continue
        lines.append(f"{front}\t{back}\t{meaning}")
    return lines


def build_decks() -> dict[str, int]:
    raw = urllib.request.urlopen(SOURCE_URL, timeout=120).read().decode("utf-8")
    grouped = _rows_by_level(raw)
    os.makedirs(DECKS_DIR, exist_ok=True)

    counts: dict[str, int] = {}
    for suffix, (_, title) in LEVELS.items():
        path = os.path.join(DECKS_DIR, f"tocfl{suffix}.txt")
        lines = _deck_lines(title, grouped[suffix])
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        count = len(lines) - _HEADER_LINES
        counts[suffix] = count
        print(f"Wrote {count:4d} cards to {path}")
    return counts


if __name__ == "__main__":
    build_decks()
