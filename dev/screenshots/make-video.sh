#!/usr/bin/env bash
# Regenerates screenshots/animations.{mp4,webp} and animations-poster.png (10-15 minutes).
# Usage: make-video.sh [--work DIR] [--out DIR] [--from-raw DIR]
#   --work DIR      raw recordings (default: a new directory under ${M3E_BENCH_OUT:-<repo>/dev/out}/video)
#   --out DIR       destination (default: <repo>/screenshots)
#   --from-raw DIR  skip the recording and only cut an earlier --work directory again
# The Shell animations are recorded in slow motion (org.gnome.Shell.Screencast of the nested Shell, scenes in video.py),
# a dark session for every scene and a light one for the last; mkvideo.py retimes, cuts and encodes, smoothness.py checks
# the result (a recording is repeated up to 3 times if it is not smooth). Same privacy guards as
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
# The scenes write three settings, in the PRIVATE dconf of the nested session only: these are the real values before
# and after (capture.sh's own guard compares the modification time of the real database, which the real session also
# bumps while a recording of a few minutes runs: that alone is not a failure here, a changed value is).
real_settings() {
    local k
    for k in "org.gnome.desktop.a11y always-show-universal-access-status" "org.gnome.desktop.wm.preferences visual-bell" \
        "org.gnome.desktop.notifications show-banners" "org.gnome.desktop.interface enable-animations"; do
        # shellcheck disable=SC2086  # schema and key, two words
        gsettings get $k 2>/dev/null || echo unavailable
    done
}
# record MODE: capture.sh, tolerating only the mtime-guard report when the scenario itself succeeded.
record() {
    local mode="$1" code=0
    "$HERE/capture.sh" --out "$WORK/$mode" --modes "$mode" --scenarios "video-$mode" || code=$?
    if [[ $code -ne 0 ]] && ! grep -q '"ok": *true' "$WORK/$mode/$mode/video-$mode.json" 2>/dev/null; then
        echo "recording of the $mode session failed" >&2
        exit 1
    fi
}
smooth() { # DIR: gate on the retimed lossless frames of DIR/out (see smoothness.py)
    "$PY" "$HERE/smoothness.py" "$1/out/lossless.mkv" --exact --active 0.1 --gate | tail -4
}
mkdir -p "$OUT"
if [[ -n "$RAW" ]]; then
    "$PY" "$HERE/mkvideo.py" --dark "$RAW/dark" --light "$RAW/light" --out "$OUT"
    echo "raw recordings in $RAW (do not publish them)"
    exit 0
fi
mkdir -p "$WORK"
# The Shell shares the machine with whatever else runs on it: a recording can have a stall. Every attempt is cut and
# measured on its retimed frames; a stretch of motion with a gap over 40 ms fails the attempt, which is then repeated.
for attempt in 1 2 3; do
    A="$WORK/attempt-$attempt"
    mkdir -p "$A"
    SETTINGS_BEFORE="$(real_settings)"
    WORK_SAVED="$WORK"; WORK="$A"
    record dark
    record light
    WORK="$WORK_SAVED"
    [[ "$(real_settings)" == "$SETTINGS_BEFORE" ]] || { echo "a real gsettings value changed during the recording: please check" >&2; exit 1; }
    "$PY" "$HERE/mkvideo.py" --dark "$A/dark" --light "$A/light" --out "$A/out" --lossless "$A/out/lossless.mkv"
    if report="$(smooth "$A")" && ! grep -q "not smooth" <<<"$report"; then
        echo "$report"
        cp "$A/out/animations.mp4" "$A/out/animations.webp" "$A/out/animations-poster.png" "$OUT/"
        echo "raw recordings kept in $A (do not publish them)"
        exit 0
    fi
    echo "attempt $attempt: $report" >&2
done
echo "no smooth recording after 3 attempts (last one in $WORK/attempt-3/out, not copied): the machine is too busy" >&2
exit 1
