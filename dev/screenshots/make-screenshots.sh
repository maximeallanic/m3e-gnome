#!/usr/bin/env bash
# Regenerates every file of screenshots/ (about 6 minutes): main run (dark and light), one palette run per wallpaper,
# then compose.py. Usage: make-screenshots.sh [--work DIR] [--out DIR]
#   --work DIR  raw captures (default: a new directory under ${M3E_BENCH_OUT:-<repo>/dev/out}/screenshots)
#   --out DIR   destination (default: <repo>/screenshots)
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
WORK="${M3E_BENCH_OUT:-$REPO/dev/out}/screenshots/$(date +%Y%m%d-%H%M%S)"
OUT="$REPO/screenshots"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --work) WORK="${2:?}"; shift 2 ;;
        --out) OUT="${2:?}"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
PY="${M3E_SHOTS_PYTHON:-$HERE/.venv/bin/python}"
[[ -x "$PY" ]] || "$HERE/setup.sh"
mkdir -p "$WORK"
"$HERE/capture.sh" --out "$WORK/main" --wallpaper dunes
for wallpaper in dunes ocean dusk forest; do
    "$HERE/capture.sh" --out "$WORK/palette/$wallpaper" --wallpaper "$wallpaper" --modes dark --scenarios palette
done
"$PY" "$HERE/compose.py" --raw "$WORK/main" --out "$OUT" --palette-raw "$WORK/palette"
echo "raw captures kept in $WORK"
