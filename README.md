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

Copy CJK fonts to `fonts/NotoSansTC-Regular.otf` if characters show as boxes.

## Project layout

```
shilin-trainer/          # repo folder may still be named bopomofo locally
  main.py
  decks/
  game/
    config.py            # PROJECT_NAME, PORT_SLUG
    cards.py
    data.py
    app.py
  port/
    shilin-trainer.sh    # → ROMS/Ports/ShilinTrainer.sh
    shilin-trainer.gptk
```

## License

MIT — use and modify freely.
