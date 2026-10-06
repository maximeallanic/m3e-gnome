#!/usr/bin/env bash
# Build the .deb, unpack it into a throw-away root (never dpkg -i), make the unpacked tree read-only and run the
# whole install -> verify -> uninstall round trip from it, so that we know the packaged tree never writes inside
# itself. Also checks the package metadata, wrappers, man pages and completion.
#
# M3E_TEST_OFFLINE=1: bundle the palette from tools/material-palette/node_modules instead of running npm ci.
set -uo pipefail
# shellcheck source=tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

command -v dpkg-deb >/dev/null || { echo "skip: dpkg-deb not installed"; exit 0; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/m3e-deb.XXXXXX")"
cleanup() { chmod -R u+w "$tmp" 2>/dev/null; rm -rf -- "${tmp:?}"; }
trap cleanup EXIT

version="$(sed -n 's/^M3E_VERSION=//p' "$SRC_REPO/lib/common.sh")"
args=(--out "$tmp/out")
if [[ -n "${M3E_TEST_OFFLINE:-}" ]]; then
    ( cd "$SRC_REPO/tools/material-palette" && node_modules/.bin/esbuild palette.mjs --bundle --platform=node --format=esm \
        --log-level=warning --outfile="$tmp/palette.mjs" ) || { echo "cannot bundle the palette offline"; exit 1; }
    args+=(--palette-bundle "$tmp/palette.mjs")
fi
echo "== build"
if bash "$SRC_REPO/scripts/build-deb.sh" "$version" "${args[@]}" >"$tmp/build.out" 2>&1; then pass "package built"
else fail "build failed"; cat "$tmp/build.out"; exit 1; fi
deb="$tmp/out/m3e-gnome_${version}_all.deb"
check_not "a VERSION that differs from M3E_VERSION is refused" bash "$SRC_REPO/scripts/build-deb.sh" 9.9.9 "${args[@]}"

echo "== metadata"
control="$(dpkg-deb -f "$deb")"
check "architecture all" grep -qx 'Architecture: all' <<<"$control"
check "depends on python3 >= 3.9, rsync, curl, git" grep -q '^Depends: python3 (>= 3.9), rsync, curl, git' <<<"$control"
check "recommends the companion extensions package" grep -q '^Recommends: .*gnome-shell-extension-m3e' <<<"$control"
dpkg-deb -e "$deb" "$tmp/ctl"
check "only a postinst maintainer script" test "$(find "$tmp/ctl" -type f -printf '%f\n' | sort | tr '\n' ' ')" = "control postinst "
check "postinst only prints" bash -c "! grep -v -E '^(#!|set -e|if |fi|exit 0|[[:space:]]*echo )' '$tmp/ctl/postinst'"
check "postinst tells to run the installer as the user" grep -q 'm3e-gnome-install' "$tmp/ctl/postinst"
check "files are owned by root" bash -c "! dpkg-deb -c '$deb' | awk '{print \$2}' | grep -qvx 'root/root'"
check "nothing outside /usr" bash -c "! dpkg-deb -c '$deb' | awk '{print \$6}' | grep -v -E '^\./(usr(/.*)?)?$' | grep -q ."

echo "== contents"
X="$tmp/root"
dpkg -x "$deb" "$X"
T="$X/usr/share/m3e-gnome"
check "palette bundle shipped" test -s "$T/tools/material-palette/dist/palette.mjs"
check "installer, helper and templates shipped" bash -c "cd '$T' && test -x install.sh && test -x gdm/m3e-gdm && test -d theme/shell && test -f LICENSE && test -f NOTICE.md && test -f docs/gdm.md"
check_not "no tests, node_modules or caches shipped" bash -c "find '$T' \\( -name tests -o -name node_modules -o -name __pycache__ -o -name .test \\) | grep -q ."
check "man pages for the three commands" bash -c "cd '$X/usr/share/man/man1' && gzip -dc m3e-gnome-install.1.gz m3e-gnome-uninstall.1.gz m3e-gnome-verify.1.gz | grep -c '^.TH' | grep -qx 3"
if command -v groff >/dev/null; then
    check "man pages render without warnings" bash -c "gzip -dc '$X/usr/share/man/man1/m3e-gnome-install.1.gz' | groff -man -ww -z 2>&1 | wc -c | grep -qx 0"
fi

echo "== completion lists match --help"
for s in install uninstall verify; do
    helped="$(bash "$T/$s.sh" --help 2>&1 | grep -o -E '(^|[ |,])(-[a-zA-Z]|--[a-z][a-z-]*)' | tr -d ' |,' | sort -u)"
    # The flags listed for this command: its `flags="..."` assignment in the completion file.
    listed="$(awk -v n="m3e-gnome-$s" '$0 ~ "^ *"n"\\)" {on=1} on {print} on && /"$/ && /flags=/ || on && /"( ;;)?$/ {exit}' \
        "$SRC_REPO/packaging/m3e-gnome.bash" | grep -o -E -- '(^|[ "])-{1,2}[a-zA-Z][a-zA-Z-]*' | tr -d ' "' | sort -u)"
    missing="$(comm -23 <(printf '%s\n' "$helped") <(printf '%s\n' "$listed") | tr '\n' ' ')"
    if [[ -z "$missing" ]]; then pass "m3e-gnome-$s: every flag of --help is completed"; else fail "m3e-gnome-$s: not completed: $missing"; fi
done

echo "== wrappers"
check "wrapper forwards --version" bash -c "[ \"\$('$X/usr/bin/m3e-gnome-install' --version)\" = 'm3e-gnome $version' ]"
check "wrapper forwards --help" bash -c "'$X/usr/bin/m3e-gnome-uninstall' --help | grep -q -- '--dry-run'"
check "a wrapper called through a symlink still finds the tree" bash -c "ln -s '$X/usr/bin/m3e-gnome-verify' '$tmp/link' && '$tmp/link' --help | grep -q -- '--strict'"
if command -v fakeroot >/dev/null; then
    out="$(fakeroot "$X/usr/bin/m3e-gnome-install" --dry-run 2>&1)"; rc=$?
    check "wrapper refuses to run as root" test "$rc" -ne 0
    check "…with an explanation" grep -q 'not as root' <<<"$out"
else
    echo "  skip  root refusal (fakeroot not installed)"
fi

echo "== round trip from the read-only unpacked package"
tree_state() { find "$T" -printf '%p %y %m %s %l\n' | sort; find "$T" -type f -exec sha256sum {} + | sort; }
chmod -R a-w "$X"
before_state="$(tree_state)"
export M3E_TEST_REPO="$T"
bash "$SRC_REPO/tests/roundtrip.sh" >"$tmp/roundtrip.out" 2>&1
rc=$?
tail -n 3 "$tmp/roundtrip.out"
if ((rc == 0)); then pass "install, verify, reinstall and uninstall work from the read-only tree"
else fail "round trip from the package failed"; grep -E 'FAIL|error' "$tmp/roundtrip.out" | head -20; fi
if [[ "$(tree_state)" == "$before_state" ]]; then pass "nothing was added, removed or changed inside the package tree"
else fail "the package tree changed during the round trip"; fi
chmod -R u+w "$X"

echo
if ((FAILS)); then echo "deb: $FAILS failure(s)"; exit 1; fi
echo "deb: all checks passed"
