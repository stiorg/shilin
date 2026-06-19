# Bopomofo Training (Pygame)

Zhuyin (Bopomofo) → Pinyin quiz with spaced repetition for **PC** and **Anbernic RG34XXSP** running **muOS**.

Native resolution: **720×480** (RG34XXSP screen).

## Features

- 37 Bopomofo symbols with 5-choice Pinyin answers
- SRS intervals — correct answers double the interval (up to Lv.32)
- Mistake-aware distractors from your wrong answers
- Endless streak mode and focused 5-pack mode
- Progress saved to `bopomofo_srs_data.json`

## PC — Quick start

```bash
cd bopomofo
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

Menu: **1** Endless, **2** Pack, **0** Exit

### Controls (RG34XXSP)

- **D-pad** — move selection
- **A** — confirm
- **B** — back to menu
- **Start + Select** — quit to muOS

(No number keys on handheld — options show without [1] labels.)

## Sync to Anbernic (Windows)

```bat
sync-anbernic.bat
```

Default target in `credentials.txt`. Pass another IP as the first argument.

Does not upload `libs/` (keep pygame on the device).

**Passwordless sync (one-time):**

```bat
setup-ssh-keys.bat
```

## muOS (RG34XXSP)

1. Copy the entire `bopomofo` folder to `/mnt/mmc/ports/bopomofo/`
2. Copy `port/bopomofo.sh` to **`/mnt/mmc/ROMS/Ports/Bopomofo.sh`** (binary upload — Windows CRLF breaks the script)
3. `chmod +x /mnt/mmc/ROMS/Ports/Bopomofo.sh`
4. Assign core: Explore Content → Ports → **Select** → Assign Core → **External - Ports**

Install pygame on device (SSH):

```bash
pip3 install --user pygame
```

**Zhuyin font:** If characters show as boxes, copy a CJK font to  
`/mnt/mmc/ports/bopomofo/fonts/NotoSansTC-Regular.otf`

After a failed launch, check logs:

1. `/mnt/mmc/ports/bopomofo/log.txt`
2. `/mnt/mmc/ROMS/Ports/bopomofo.log`
3. `/tmp/bopomofo.log`

See `port/MUOS-PORTING-NOTES.txt` for troubleshooting.

## Project layout

```
bopomofo/
  main.py              # Entry point (pygame + muOS bootstrap)
  requirements.txt
  game/
    config.py          # 720×480, handheld detection
    data.py            # Dictionary + save/load
    srs.py             # Endless & pack session logic
    input_handler.py
    renderer.py
    app.py             # Menu + quiz UI
  port/
    bopomofo.sh        # copy to ROMS/Ports/Bopomofo.sh
    bopomofo.gptk      # gptokeyb button mapping
  fonts/               # optional CJK font for handheld
```

## License

MIT — use and modify freely.
