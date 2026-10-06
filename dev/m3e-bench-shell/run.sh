#!/usr/bin/env bash
# Shell style bench: theme palettes (dark and light) -> nested Shell (nested.sh of the m3e-gnome-extensions repository,
# through dev/m3e-bench/nested-launcher.sh; bench extension m3e-bench-style) -> measure.py per mode -> report_shell.py.
# Output: ${M3E_BENCH_OUT:-<repo>/dev/out}/m3e-bench-shell/<date>/{dark/, light/, report.html, nested/shell.log,
# nested-gdm/, extension/}.
#
# Usage: run.sh [--batch N] [--surfaces a,b] [--out DIR] [--candidate FILE] [--locale LOC] [--fake-remote]
#   --batch N        surfaces of the rows of batch N (expected/), plus those of the witnesses
#   --surfaces a,b   explicit list (replaces the batch's)
#   --out DIR        output directory (default: see above)
#   --candidate FILE candidate sheet imposed for both modes (default: the theme rendered by render_theme.py)
#   --locale LOC     locale of the nested Shell ($M3E_BENCH_LOCALE, default C.UTF-8); text widths depend on it
#   --fake-remote    `search` surface: fake in-process remote search provider; the scenario must fail (guard test)
#   --self-test      run the slow tests (tests/test_run.py: broken sheets, guards, with real nested Shells)
# Surfaces of the login screen (expected.SURFACES_GDM) run in a second nested Shell in gdm mode (nested-gdm/).
# Environment: M3E_BASE_THEME (base theme, read only; default ~/.themes/Material-Gnome), M3E_BENCH_OUT, M3E_BENCH_LOCALE,
# M3E_EXTENSIONS_REPO (see dev/m3e-bench/nested-launcher.sh).
# Exit code 0 if there is no deviation in either mode and no CSS parse error in shell.log.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# shellcheck source=../m3e-bench/nested-launcher.sh
source "$REPO/dev/m3e-bench/nested-launcher.sh" || exit 2
MEASURE="$REPO/dev/m3e-bench/measure.py"
UUID='m3e-bench-style@maximeallanic.github.io'
export M3E_BASE_THEME="${M3E_BASE_THEME:-$HOME/.themes/Material-Gnome}"
MODES=(dark light)
# Where the bench extension of the extensions repository keeps the logind guard and the wait helper (copied at run
# time, never duplicated: the nested Shell must not reach the real logind session).
SHARED_BENCH_EXT="$M3E_EXTENSIONS_REPO/tests/bench/bench-extension/m3e-bench@maximeallanic.github.io"
# Messages of St (and of libcroco, its parser) for a rejected sheet, recorded in shell.log on deliberately broken
# sheets (tests/test_run.py):
#   "parsing error: 7:27:could not recognize next production"                        (libcroco, on stderr)
#   "St-WARNING **: ...: Error parsing stylesheet 'file:///.../candidate-dark.css'; errcode:15"
#     -> syntax error: the WHOLE sheet is dropped;
#   "percentage lengths not currently supported" (width: calc(100% - 60px));
#   "Ignoring length property that isn't a number at line N, col M", "Ignoring invalid type of number of
#     length property", "Ignoring excess values in shadow definition" (st-theme-node.c, when read).
# An unknown property (`colour: red`) or an unknown unit (`width: 12qq`) leaves NO trace, even read on an actor:
# st_sheet.py looks for them before the launch (static check).
CSS_ERROR_PATTERN="Error parsing stylesheet|^parsing error: |Ignoring length property that isn't a number|Ignoring invalid type of number of length property|Ignoring excess values in shadow definition|percentage lengths not currently supported|Percentages not supported for border-image"

BATCH=''; SURFACES=''; CANDIDATE=''; OUT=''; LOCALE="$BENCH_LOCALE"; TEST_ENV=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch) BATCH="${2:?batch number}"; shift 2 ;;
        --surfaces) SURFACES="${2:?list of surfaces}"; shift 2 ;;
        --candidate) CANDIDATE="${2:?file}"; shift 2 ;;
        --out) OUT="${2:?directory}"; shift 2 ;;
        --locale) LOCALE="${2:?locale}"; shift 2 ;;
        --fake-remote) TEST_ENV+=(--env M3E_BENCH_STYLE_FAKE_REMOTE=1); shift ;;
        --self-test)
            cd "$HERE/tests" && M3E_BENCH_SHELL_SLOW=1 exec python3 -m unittest -v test_run ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
[[ -z "$BATCH" || "$BATCH" =~ ^[0-9]+$ ]] || { echo "--batch expects a number: $BATCH" >&2; exit 2; }
[[ -z "$CANDIDATE" || -f "$CANDIDATE" ]] || { echo "candidate sheet not found: $CANDIDATE" >&2; exit 2; }
[[ -d "$M3E_BASE_THEME" ]] || { echo "base theme not found: $M3E_BASE_THEME (set M3E_BASE_THEME)" >&2; exit 2; }
for f in logind-guard.js tools.js; do
    [[ -f "$SHARED_BENCH_EXT/$f" ]] || { echo "not found: $SHARED_BENCH_EXT/$f" >&2; exit 2; }
done

[[ -n "$OUT" ]] || OUT="${M3E_BENCH_OUT:-$REPO/dev/out}/m3e-bench-shell/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT" || exit 2
OUT="$(cd "$OUT" && pwd)"
echo "out: $OUT"

# --- surfaces ---
if [[ -z "$SURFACES" ]]; then
    SURFACES="$(cd "$HERE" && python3 -m expected "$BATCH")" || exit 2
fi
[[ "$SURFACES" =~ ^[A-Za-z0-9_-]+(,[A-Za-z0-9_-]+)*$ ]] || { echo "invalid surfaces: '$SURFACES'" >&2; exit 2; }

# --- palettes and sheets, one directory per mode (seed = fallback_color of the theme: reproducible palette) ---
python3 "$HERE/palettes.py" --out "$OUT" --base-theme "$M3E_BASE_THEME" || exit 2

# --- copy of the bench extension with its sheets ---
EXT="$OUT/extension/$UUID"
mkdir -p "$OUT/extension" || exit 2
cp -r "$HERE/$UUID" "$EXT" || exit 2
cp "$SHARED_BENCH_EXT/logind-guard.js" "$SHARED_BENCH_EXT/tools.js" "$EXT/" || exit 2
mkdir -p "$EXT/sheets"
for mode in "${MODES[@]}"; do
    cp "$REPO/dev/reference/shell-stock/gnome-shell-$mode.css" "$EXT/sheets/stock-$mode.css" || exit 2
    cp "${CANDIDATE:-$OUT/$mode/gnome-shell.css}" "$EXT/sheets/candidate-$mode.css" || exit 2
done
# Images of the candidate sheet (url("assets/...") relative to the sheet): the base theme's, when it has any.
if [[ -d "$M3E_BASE_THEME/gnome-shell/assets" ]]; then
    cp -rL "$M3E_BASE_THEME/gnome-shell/assets" "$EXT/sheets/assets" || exit 2
fi

status=0
# --- static check of the candidate sheets (declarations St would ignore without a word) ---
: >"$OUT/css-errors.txt"
for mode in "${MODES[@]}"; do
    python3 "$HERE/st_sheet.py" "$EXT/sheets/candidate-$mode.css" >>"$OUT/css-errors.txt"
done
if [[ -s "$OUT/css-errors.txt" ]]; then
    echo "candidate sheet: declarations ignored by St ($(wc -l <"$OUT/css-errors.txt")):" >&2
    head -20 "$OUT/css-errors.txt" >&2
    status=1
else
    rm -f "$OUT/css-errors.txt"
fi

# --- nested Shells (nested.sh only; never gnome-shell directly) ---
# At most two: user mode (nested/) and login screen mode (nested-gdm/, surfaces of expected.SURFACES_GDM). Same
# extension, same output of the captures.
GDM_ALL=",$(cd "$HERE" && python3 -m expected --gdm),"
USER_SURFACES=''; GDM_SURFACES=''
IFS=',' read -ra SURFACE_LIST <<<"$SURFACES"
for s in "${SURFACE_LIST[@]}"; do
    if [[ "$GDM_ALL" == *",$s,"* ]]; then GDM_SURFACES+="$s,"; else USER_SURFACES+="$s,"; fi
done
LOGS=()
run_nested() { # mode surfaces directory
    local mode="$1" surfaces="${2%,}" dir="$3" scenarios code
    [[ -n "$surfaces" ]] || return 0
    scenarios="$(tr ',' '\n' <<<"$surfaces" | while read -r s; do printf '%s:dark,%s:light,' "$s" "$s"; done)"
    scenarios="${scenarios%,}"
    LOGS+=("$OUT/$dir/shell.log")
    bash "$NESTED_SH" --mode "$mode" --extension "$EXT" --locale "$LOCALE" --env "M3E_BENCH_STYLE_OUT=$OUT" \
        ${TEST_ENV[@]+"${TEST_ENV[@]}"} --scenarios "$scenarios" --out "$OUT/$dir"
    code=$?
    if [[ $code -eq 3 ]]; then
        echo "dconf guard triggered (see the nested.sh message above)" >&2
        status=1
    elif [[ $code -eq 4 ]]; then
        echo "XDG_RUNTIME_DIR guard triggered (see the nested.sh message above)" >&2
        status=1
    elif [[ $code -ne 0 ]]; then
        echo "nested.sh ($mode) failed (code $code, see $OUT/$dir/shell.log)" >&2
        status=1
    fi
}
run_nested user "$USER_SURFACES" nested
run_nested gdm "$GDM_SURFACES" nested-gdm

# --- CSS parse errors (St silently ignores a rejected declaration) ---
if [[ ${#LOGS[@]} -gt 0 ]] && cat "${LOGS[@]}" 2>/dev/null | grep -E -- "$CSS_ERROR_PATTERN" >"$OUT/css-errors-shell.txt"; then
    echo "CSS parse errors in shell.log ($(wc -l <"$OUT/css-errors-shell.txt")):" >&2
    head -20 "$OUT/css-errors-shell.txt" >&2
    status=1
else
    rm -f "$OUT/css-errors-shell.txt"
fi

# --- measurement and report ---
for mode in "${MODES[@]}"; do
    echo "== measure $mode =="
    python3 "$MEASURE" "$OUT/$mode" || status=1
done
python3 "$HERE/report_shell.py" "$OUT" || status=1
echo "report: $OUT/report.html"
exit "$status"
