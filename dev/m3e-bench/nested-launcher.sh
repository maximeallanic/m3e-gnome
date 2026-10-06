# Sourced by the benches that need a nested, headless GNOME Shell. Sets NESTED_SH to the launcher of the
# m3e-gnome-extensions repository (tests/bench/nested.sh), which owns every isolation guard: --headless
# --virtual-monitor, named Wayland socket, private XDG_* and XDG_RUNTIME_DIR exported before dbus-run-session,
# private dconf, logind neutralised by the bench extension, dconf and runtime-directory guards (exit codes 3 and 4).
# Benches must not start gnome-shell any other way.
#
# Location: $M3E_EXTENSIONS_REPO (default: ../m3e-gnome-extensions next to this repository).
# Locale of the nested Shell: $M3E_BENCH_LOCALE (default C.UTF-8); the host locale is never inherited.
_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
M3E_EXTENSIONS_REPO="${M3E_EXTENSIONS_REPO:-$(cd "$_here/../../.." && pwd)/m3e-gnome-extensions}"
NESTED_SH="$M3E_EXTENSIONS_REPO/tests/bench/nested.sh"
BENCH_LOCALE="${M3E_BENCH_LOCALE:-C.UTF-8}"
if [[ ! -f "$NESTED_SH" ]]; then
    echo "nested launcher not found: $NESTED_SH" >&2
    echo "check out the m3e-gnome-extensions repository next to this one, or set M3E_EXTENSIONS_REPO" >&2
    return 2 2>/dev/null || exit 2
fi
unset _here
