#!/usr/bin/env bash
# GTK motion bench. Plays real GTK applications (Ptyxis, Files, Calculator, Settings) and two bench clients
# (client-gtk4.py, client-gtk3.py) inside a nested, headless GNOME Shell started by nested.sh of the
# m3e-gnome-extensions repository (it owns every isolation guard: private XDG_*, XDG_RUNTIME_DIR and session bus,
# named Wayland socket, private dconf, logind cut; see dev/m3e-bench/nested-launcher.sh). The applications run with
# the Material-Gnome base theme (copied, read only source), a fixed palette rendered by dev/m3e-bench/render_theme.py,
# and the M3E GTK overrides of the repository; the pointer and keyboard are virtual devices of the nested Shell,
# driven by the bench extension (m3e-bench-gtk@maximeallanic.github.io). The bench counts the "reported min
# width/height" GTK warnings and the CSS errors. It never touches the real session: no write in ~/.config,
# ~/.themes or the real dconf (nested.sh checks it: exit codes 3 and 4).
#
# Usage: run.sh [--modes dark,light] [--scenarios s1,s2,...] [--overrides DIR] [--out DIR] [--locale LOC]
#   --overrides DIR  directory of the M3E stylesheets to try (flat, like an installed copy); default: theme/overrides
#                    and theme/motion/gtk of this repository. Read only.
#   --scenarios      client4, client3, ptyxis, files, calculator, settings (default: all)
#   --locale LOC     locale of the nested Shell and its applications (default $M3E_BENCH_LOCALE, else C.UTF-8)
# Environment: M3E_BASE_THEME (base theme, default ~/.themes/Material-Gnome, read only), M3E_EXTENSIONS_REPO
#   (default ../m3e-gnome-extensions), M3E_BENCH_OUT (default output root: <repo>/dev/out).
# Fixed settings of the applications (documented in stage.py): neutral Ptyxis profile with the built-in "gnome"
# palette, icon theme Material-Symbols (repository), system default fonts: nothing is read from the real session.
# Output: <out>/<mode>/{journal-*.log, driver-*.log, shell.log, *.png, *.json}, <out>/summary.json.
# Exit code: 0 when no "reported min width/height", no CSS error and no unmet expectation; 1 otherwise or when a
# scenario failed; 2 refusal/usage; 3 real dconf changed; 4 host runtime directory changed (both from nested.sh).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# shellcheck source=../m3e-bench/nested-launcher.sh
source "$REPO/dev/m3e-bench/nested-launcher.sh" || exit 2

MODES='dark,light'
SCENARIOS='client4,client3,ptyxis,files,calculator,settings'
OVERRIDES=''
OUT="${M3E_BENCH_OUT:-$REPO/dev/out}/m3e-bench-gtk/$(date +%Y%m%d-%H%M%S)"
LOCALE="$BENCH_LOCALE"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --modes) MODES="${2:?}"; shift 2 ;;
        --scenarios) SCENARIOS="${2:?}"; shift 2 ;;
        --overrides) OVERRIDES="${2:?}"; shift 2 ;;
        --out) OUT="${2:?}"; shift 2 ;;
        --locale) LOCALE="${2:?}"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
[[ "$SCENARIOS" =~ ^[a-z0-9]+(,[a-z0-9]+)*$ && "$MODES" =~ ^(dark|light)(,(dark|light))*$ ]] ||
    { echo "invalid scenarios or modes" >&2; exit 2; }
[[ -z "$OVERRIDES" || -d "$OVERRIDES" ]] || { echo "--overrides: no such directory: $OVERRIDES" >&2; exit 2; }
mkdir -p "$OUT" && OUT="$(cd "$OUT" && pwd)" || exit 2

global_code=0
IFS=',' read -ra MODE_LIST <<<"$MODES"
for MODE in "${MODE_LIST[@]}"; do
    MODE_OUT="$OUT/$MODE"
    mkdir -p "$MODE_OUT" || exit 2
    stage_args=(--out "$MODE_OUT" --mode "$MODE" --extensions-repo "$M3E_EXTENSIONS_REPO")
    [[ -n "$OVERRIDES" ]] && stage_args+=(--overrides "$OVERRIDES")
    python3 "$HERE/stage.py" "${stage_args[@]}" || { echo "stage.py failed ($MODE)" >&2; exit 1; }
    "$NESTED_SH" --scenarios "$SCENARIOS" --out "$MODE_OUT" --locale "$LOCALE" \
        --extension "$MODE_OUT/stage/extension" --dconf-keyfile "$MODE_OUT/settings.keyfile" \
        --env "M3E_BENCH_GTK_STAGE=$MODE_OUT/stage" --env "M3E_BENCH_GTK_SCRIPTS=$HERE" \
        --env "M3E_BENCH_MODE=$MODE"
    code=$?
    [[ $code -ne 0 && $global_code -eq 0 ]] && global_code=$code
done
python3 "$HERE/summary.py" "$OUT" || [[ $global_code -ne 0 ]] || global_code=1
echo "output: $OUT"
exit $global_code
