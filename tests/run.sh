#!/usr/bin/env bash
# Installer tests: static checks, then the install/verify/uninstall round trip and the guard tests, all inside a
# throw-away HOME with fake GNOME tools (see tests/lib.sh). Exit status is non-zero on any failure.
#
#   tests/run.sh
# Environment: M3E_TEST_OFFLINE=1 (stub npm ci), M3E_TEST_NETWORK=1 (also build the cursor from AOSP),
#   M3E_TEST_NO_MATUGEN=1 (download the pinned matugen instead of using the one on PATH),
#   M3E_TEST_EXTENSIONS_REPO=DIR (also install from a real m3e-gnome-extensions checkout), M3E_TEST_KEEP=1.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$HERE")"
status=0

shell_files() { # every shell script of the installer
    ( cd "$REPO" && printf '%s\n' install.sh uninstall.sh verify.sh lib/*.sh gdm/*.sh gdm/m3e-gdm tests/*.sh tests/shims/fc-cache \
        tests/shims/fc-list tests/shims/gnome-shell tests/shims/gtk-update-icon-cache )
}

echo "== syntax"
while IFS= read -r f; do
    bash -n "$REPO/$f" || { echo "syntax error: $f"; status=1; }
done < <(shell_files)
python3 -m py_compile "$REPO/lib/enabled_extensions.py" "$REPO/gdm/ingest.py" "$HERE/snapshot.py" "$HERE"/shims/{_fake.py,gsettings,dconf,gnome-extensions,systemctl} ||
    status=1
find "$REPO/lib" "$REPO/gdm" "$HERE" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

echo "== file size (500 lines max)"
while IFS= read -r f; do
    n="$(wc -l <"$REPO/$f")"
    if ((n > 500)); then echo "too long: $f ($n lines)"; status=1; fi
done < <(cd "$REPO" && printf '%s\n' install.sh uninstall.sh verify.sh lib/* gdm/* tests/*.sh tests/*.py tests/shims/*)

echo "== shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
    ( cd "$REPO" && shell_files | xargs shellcheck -x ) || status=1
else
    echo "shellcheck not installed: skipped (apt install shellcheck / pip install shellcheck-py)"
fi

for t in roundtrip test_guards test_gdm_input test_gdm; do
    echo
    echo "== $t"
    bash "$HERE/$t.sh" || status=1
done

echo
if ((status)); then echo "TESTS FAILED"; else echo "all installer tests passed"; fi
exit "$status"
