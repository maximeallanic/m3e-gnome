#!/usr/bin/env bash
# Regenerates screenshots/animations.{mp4,webp} and animations-poster.png (about 6 minutes).
# Usage: make-video.sh [--work DIR] [--out DIR] [--from-raw DIR]
#   --work DIR      raw recordings (default: a new directory under ${M3E_BENCH_OUT:-<repo>/dev/out}/video)
#   --out DIR       destination (default: <repo>/screenshots)
#   --from-raw DIR  skip the recording and only cut an earlier --work directory again
# The Shell animations are recorded in real time (org.gnome.Shell.Screencast of the nested Shell, scenes in video.py), a
# dark session for every scene and a light one for the last; mkvideo.py cuts and encodes. Same privacy guards as
# capture.sh (private system bus, audio, session bus and home): look at the frames before publishing.
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
WORK="${M3E_BENCH_OUT:-$REPO/dev/out}/video/$(date +%Y%m%d-%H%M%S)"
OUT="$REPO/screenshots"
RAW=''
while [[ $# -gt 0 ]]; do
    case "$1" in
        --work) WORK="${2:?}"; shift 2 ;;
        --out) OUT="${2:?}"; shift 2 ;;
        --from-raw) RAW="${2:?}"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
PY="${M3E_SHOTS_PYTHON:-$HERE/.venv/bin/python}"
[[ -x "$PY" ]] || "$HERE/setup.sh"
command -v ffmpeg >/dev/null || { echo "ffmpeg is required" >&2; exit 2; }
if [[ -n "$RAW" ]]; then
    WORK="$RAW"
else
    mkdir -p "$WORK"
    "$HERE/capture.sh" --out "$WORK/dark" --modes dark --scenarios video-dark
    "$HERE/capture.sh" --out "$WORK/light" --modes light --scenarios video-light
fi
mkdir -p "$OUT"
"$PY" "$HERE/mkvideo.py" --dark "$WORK/dark" --light "$WORK/light" --out "$OUT"
echo "raw recordings kept in $WORK (do not publish them)"
