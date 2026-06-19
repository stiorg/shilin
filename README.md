# Shilin Trainer (Pygame)

**Shilin Trainer** — Bopomofo drills + **Anki flashcard** character study for **PC** and **Anbernic RG34XXSP** (muOS).

Native resolution: **720×480** (RG34XXSP screen).

## Features

**Bopomofo** (built-in)
- 37 Zhuyin symbols → 5-choice Pinyin quiz
- SRS intervals, mistake-aware distractors, endless + 5-pack modes

**Character flashcards** (Anki decks)
- Load decks from `decks/` — `.apkg` or Anki plain-text `.txt`
- Shows the **first field** (character/word), pick the **second field** (reading/meaning)
- Same SRS engine; progress in `flashcard_srs_data.json`

## PC — Quick start

```bash
pip install -r requirements.txt
python main.py
```

### Controls (keyboard)

| Key | Action |
|-----|--------|
| **1–5** | Pick answer directly |
| Up / Down / Left / Right | Move selection |
| Enter | Confirm selection |
| Esc | Back / exit menu |

### Controls (RG34XXSP)

- **D-pad** — move selection
- **A** — confirm
- **B** — back to menu
- **Start + Select** — quit to muOS

## Anki decks

1. Export from Anki: **File → Export → Notes in Plain Text (.txt)**  
   Or copy a classic `.apkg` (must contain `collection.anki2`).
2. Put the file in `decks/`.
3. In-game: **Choose Deck…** → **Characters — Endless** or **5-Pack**.

Sample deck: `decks/sample-hsk1.txt`.

## Sync to Anbernic (Windows)

```bat
sync-anbernic.bat
```

```bat
setup-ssh-keys.bat
```

## muOS (RG34XXSP)

1. Sync to `/mnt/mmc/ports/shilin-trainer/`
2. Launcher: `/mnt/mmc/ROMS/Ports/ShilinTrainer.sh`
3. Assign core **External - Ports**
4. `pip3 install --user pygame` on the device

CJK fonts (required for ㄅㄆㄇ and Chinese characters on the handheld):

```bash
python scripts/download-fonts.py
sync-anbernic.bat
```

Without `fonts/NotoSansCJKtc-Regular.otf` on the device, Bopomofo shows as empty boxes.
Without `fonts/NotoSans-Regular.ttf`, pinyin tone marks (ǐ, ǎ, …) show as boxes.

## Project layout

```
shilin-trainer/          # repo folder may still be named bopomofo locally
  main.py
  decks/
  fonts/
    NotoSansCJKtc-Regular.otf   # scripts/download-fonts.py (~16 MB, not in git)
  game/
    config.py            # PROJECT_NAME, PORT_SLUG
    cards.py
    data.py
    app.py
  port/
    shilin-trainer.sh    # → ROMS/Ports/ShilinTrainer.sh
    shilin-trainer.gptk
  scripts/
    download-fonts.py
```

## License

MIT — use and modify freely.
