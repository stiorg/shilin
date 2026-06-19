#!/bin/bash
# Install: copy to /mnt/mmc/ROMS/Ports/ShilinTrainer.sh
#           chmod +x /mnt/mmc/ROMS/Ports/ShilinTrainer.sh

LOG_PATHS=(
  "/mnt/mmc/ports/shilin-trainer/log.txt"
  "/mnt/sdcard/ports/shilin-trainer/log.txt"
  "/mnt/mmc/ROMS/Ports/shilin-trainer.log"
  "/mnt/sdcard/ROMS/Ports/shilin-trainer.log"
  "/tmp/shilin-trainer.log"
)

log() {
  local line path
  line="$(date '+%Y-%m-%d %H:%M:%S') $*"
  for path in "${LOG_PATHS[@]}"; do
    echo "$line" >>"$path" 2>/dev/null && break
  done
}

log "=== launch start ==="
log "script=$0 pwd=$(pwd) user=$(whoami)"

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
controlfolder=""

for cf in \
  "/mnt/mmc/MUOS/PortMaster" \
  "/mnt/mmc/ROMS/ports/PortMaster" \
  "/roms/ports/PortMaster" \
  "/mnt/mmc/ROMS/Ports/PortMaster"; do
  if [ -f "$cf/control.txt" ]; then
    controlfolder="$cf"
    break
  fi
done

log "controlfolder=${controlfolder:-none}"

if [ -n "$controlfolder" ]; then
  # shellcheck source=/dev/null
  source "$controlfolder/control.txt" || log "WARN control.txt returned $?"
  if [ -f "${controlfolder}/mod_${CFW_NAME}.txt" ]; then
    # shellcheck source=/dev/null
    source "${controlfolder}/mod_${CFW_NAME}.txt" || log "WARN mod_${CFW_NAME}.txt returned $?"
  fi
  if declare -F get_controls >/dev/null 2>&1; then
    get_controls || log "WARN get_controls returned $?"
  fi
  log "directory=${directory:-unset} CFW_NAME=${CFW_NAME:-unset}"
fi

GAMEDIR=""
for candidate in \
  "/mnt/mmc/ports/shilin-trainer" \
  "/mnt/sdcard/ports/shilin-trainer" \
  "/mnt/mmc/PORTS/shilin-trainer" \
  "/mnt/sdcard/PORTS/shilin-trainer" \
  "/mnt/mmc/ports/bopomofo" \
  "/mnt/sdcard/ports/bopomofo" \
  "/${directory:-__missing__}/ports/shilin-trainer"; do
  if [ -f "$candidate/main.py" ]; then
    GAMEDIR="$candidate"
    break
  fi
done

log "GAMEDIR=${GAMEDIR:-NOT_FOUND}"

if [ -z "$GAMEDIR" ]; then
  log "ERROR main.py not found in any candidate path"
  sleep 5
  exit 1
fi

LOG_PATHS=("$GAMEDIR/log.txt" "${LOG_PATHS[@]}")
cd "$GAMEDIR" || {
  log "ERROR cd failed to $GAMEDIR"
  sleep 5
  exit 1
}

export MUOS=1
export DEVICE=RG34XXSP
export PYGAME_HIDE_SUPPORT_PROMPT=1
export SDL_AUDIODRIVER=alsa

if [ -x "/opt/python/bin/python3" ]; then
  PYTHON=/opt/python/bin/python3
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi
export PATH="/opt/python/bin:${controlfolder:+$controlfolder/muos:}$PATH"

unset PYTHONPATH
log "python=$PYTHON ($($PYTHON --version 2>&1))"

if [ -n "$controlfolder" ] && declare -F pm_platform_helper >/dev/null 2>&1; then
  pm_platform_helper "$PYTHON" || log "WARN pm_platform_helper returned $?"
  sleep 0.5
fi

log "LD_LIBRARY_PATH before sanitize=${LD_LIBRARY_PATH:-unset}"

_clean_ld=""
IFS=':' read -r -a _ldparts <<<"${LD_LIBRARY_PATH:-}"
for _p in "${_ldparts[@]}"; do
  [ -z "$_p" ] && continue
  case "$_p" in
    *frontend*) continue ;;
  esac
  _clean_ld="${_clean_ld:+$_clean_ld:}$_p"
  done
unset IFS
export LD_LIBRARY_PATH="${_clean_ld:+/usr/lib:/lib:}${_clean_ld:-/usr/lib:/lib}"

for _sdl in \
  /usr/lib/libSDL2-2.0.so.0 \
  /opt/muos/extra/lib/libSDL2-2.0.so.0 \
  /opt/python/lib/libSDL2-2.0.so.0; do
  if [ -f "$_sdl" ]; then
    export LD_PRELOAD="$_sdl"
    log "LD_PRELOAD=$_sdl"
    break
  fi
done

unset SDL_VIDEODRIVER
log "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
log "SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-auto}"

if ! "$PYTHON" -c "import pygame" 2>/dev/null; then
  log "ERROR: pygame missing for $PYTHON"
  sleep 5
  exit 1
fi
log "pygame=$("$PYTHON" -c "import pygame; print(pygame.__file__)" 2>/dev/null)"

GPTK="$GAMEDIR/port/shilin-trainer.gptk"
GPTOKEYB_BIN=""
if [ -n "${GPTOKEYB:-}" ] && [ -x "$GPTOKEYB" ]; then
  GPTOKEYB_BIN="$GPTOKEYB"
elif [ -n "$controlfolder" ] && [ -x "$controlfolder/muos/gptokeyb" ]; then
  GPTOKEYB_BIN="$controlfolder/muos/gptokeyb"
elif [ -n "$controlfolder" ] && [ -x "$controlfolder/gptokeyb" ]; then
  GPTOKEYB_BIN="$controlfolder/gptokeyb"
fi

GPTOKEYB_PID=""
if [ -n "$GPTOKEYB_BIN" ] && [ -f "$GPTK" ]; then
  export SDL_GAMECONTROLLERCONFIG="${sdl_controllerconfig:-$SDL_GAMECONTROLLERCONFIG}"
  "$GPTOKEYB_BIN" "$PYTHON" -c "$GPTK" &
  GPTOKEYB_PID=$!
  log "gptokeyb=$GPTOKEYB_BIN pid=$GPTOKEYB_PID gptk=$GPTK"
  sleep 0.2
fi

PYLOG="$GAMEDIR/log.txt"
log "running main.py (log=$PYLOG)"
"$PYTHON" -u main.py >>"$PYLOG" 2>&1
RET=$?

if [ -n "$GPTOKEYB_PID" ]; then
  kill "$GPTOKEYB_PID" 2>/dev/null || true
fi
log "main.py exited code=$RET"

if [ -n "$controlfolder" ] && declare -F pm_finish >/dev/null 2>&1; then
  pm_finish || log "WARN pm_finish returned $?"
fi

sleep 2
exit $RET
