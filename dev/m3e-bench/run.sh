#!/usr/bin/env bash
# M3 Expressive grid bench: layout -> capture -> measure -> report, for GTK 3, GTK 4 and libadwaita.
#
# Usage: run.sh --measure <folder> [--reference-images DIR]
#   Measures and reports a capture folder that already exists (layout-<name>.json, <name>.png, <name>-screen.json and
#   colors.css, as written by a capture driver): runs measure.py then report.py. Pure image analysis: it opens no
#   window, takes no screenshot and changes no setting. Exit code 0 if there is no deviation, 1 otherwise.
#
# Capturing is NOT implemented here, on purpose. The old driver opened full-screen windows in the real session,
# took screenshots through the desktop portal and toggled gsettings (colour scheme, notification banners): all of
# that is forbidden. bench.py (the window side) and capture.py (screen geometry, cropping) are kept for a nested
# capture driver: a bench extension inside the nested Shell started by nested.sh (see nested-launcher.sh) that
# starts bench.py against the nested socket, takes the screenshot with Shell.Screenshot and writes
# <name>.png / <name>-screen.json. Until that driver exists, any capture request is refused (exit 2).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOLDER=""
REFERENCES=""
while [ $# -gt 0 ]; do
    case "$1" in
        --measure) FOLDER="${2:?--measure needs a folder}"; shift 2 ;;
        --reference-images) REFERENCES="${2:?--reference-images needs a folder}"; shift 2 ;;
        --nested|--batch|--mode|--out|--screen)
            echo "run.sh: capturing is not implemented (nested capture driver missing); see the header of this" \
                 "script. Use --measure <folder> on an existing capture folder." >&2
            exit 2 ;;
        *) echo "run.sh: unknown option: $1" >&2; exit 2 ;;
    esac
done
if [ -z "$FOLDER" ]; then
    echo "run.sh: nothing to do. Usage: run.sh --measure <folder> [--reference-images DIR]" >&2
    exit 2
fi
[ -d "$FOLDER" ] || { echo "run.sh: not a folder: $FOLDER" >&2; exit 2; }
python3 "$HERE/measure.py" "$FOLDER"
code=$?
python3 "$HERE/report.py" "$FOLDER" ${REFERENCES:+"$REFERENCES"} || exit 2
exit $code
