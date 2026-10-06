#!/usr/bin/env bash
# GDM privilege boundary: everything the user-side installer hands to the root helper is untrusted DATA. Hostile or
# malformed input must be refused, and a refused run must leave the (fake) system untouched. Also: the test hooks of the
# helper must not work as root, and the helper refuses to run from a directory a user could modify.
set -uo pipefail
# shellcheck source=tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=tests/gdm_lib.sh
source "$TESTS_DIR/gdm_lib.sh"

for tool in dpkg-divert update-alternatives glib-compile-resources gresource dconf; do
    if ! command -v "$tool" >/dev/null 2>&1; then echo "skipped: $tool not installed (apt install dpkg libglib2.0-dev-bin libglib2.0-bin dconf-cli)"; exit 0; fi
done

gdm_setup
trap t_teardown EXIT
INGEST=(python3 -I "$GDM_SRC/ingest.py")
GR="$T_ROOT/root"
gdm_make_root "$GR" debian
gdm_install_helper_into "$GR"
gdm_snapshot "$GR" >"$T_ROOT/clean.snap"

fresh() { rm -rf -- "${T_ROOT:?}/data"; gdm_make_data "$T_ROOT/data"; }
rejects() { # description  (data dir is $T_ROOT/data)
    local d="$1" out rc
    out="$("${INGEST[@]}" check "$T_ROOT/data" 2>&1)"; rc=$?
    if ((rc == 1)) && grep -q 'refused' <<<"$out"; then pass "ingest refuses: $d"; else fail "ingest did not refuse: $d (rc=$rc: $out)"; fi
    out="$(gdm_run apply --from "$T_ROOT/data" 2>&1)"; rc=$?
    if ((rc != 0)); then pass "helper apply refuses: $d"; else fail "helper apply accepted: $d"; fi
    gdm_snapshot "$GR" | grep -v 'diversions-old' >"$T_ROOT/now.snap"
    if cmp -s "$T_ROOT/clean.snap" "$T_ROOT/now.snap"; then pass "…and the system is untouched"
    else fail "refused input still changed the system: $d"; diff "$T_ROOT/clean.snap" "$T_ROOT/now.snap" | head -5; fi
}
set_css() { printf '%s\n' "$1" >"$T_ROOT/data/theme.css"; }

echo "== valid data is accepted"
fresh
check "check accepts the fixture" "${INGEST[@]}" check "$T_ROOT/data"

echo "== links, special files, sizes"
fresh; mv "$T_ROOT/data/theme.css" "$T_ROOT/elsewhere.css"; ln -s "$T_ROOT/elsewhere.css" "$T_ROOT/data/theme.css"; rejects "symlinked theme.css"
fresh; ln -s /etc "$T_ROOT/data/assets/icons/Googlebook/etc"; rejects "symlink inside assets"
fresh; rm -rf "$T_ROOT/data/assets/fonts"; ln -s /usr/share/fonts "$T_ROOT/data/assets/fonts"; rejects "symlinked assets directory"
fresh; ln "$T_ROOT/data/greeter.conf" "$T_ROOT/hardlink"; rejects "hard-linked file"
fresh; mkfifo "$T_ROOT/data/assets/icons/Googlebook/pipe.png"; rejects "FIFO"
fresh; head -c $((4 * 1024 * 1024)) /dev/zero | tr '\0' 'a' >>"$T_ROOT/data/theme.css"; rejects "oversized theme.css"
fresh; head -c $((25 * 1024 * 1024)) /dev/zero >>"$T_ROOT/data/background.png"; rejects "oversized background"
fresh; head -c $((9 * 1024 * 1024)) /dev/zero >"$T_ROOT/data/assets/fonts/GoogleSansFlex/big.otf"; rejects "oversized asset"
fresh; chmod 666 "$T_ROOT/data/theme.css"; rejects "world-writable theme.css"
fresh; chmod 777 "$T_ROOT/data/assets/icons"; rejects "world-writable directory"
fresh; printf 'x' >"$T_ROOT/data/extra.sh"; rejects "unexpected top-level file"

echo "== PNG"
fresh; printf 'GIF89a not a png at all, but long enough to have a header....' >"$T_ROOT/data/background.png"; rejects "non-PNG background"
fresh; gdm_make_png "$T_ROOT/data/background.png" 100000 100000; rejects "PNG with absurd dimensions"
fresh; head -c 40 "$T_ROOT/data/background.png" >"$T_ROOT/trunc"; cp "$T_ROOT/trunc" "$T_ROOT/data/background.png"; rejects "truncated PNG"

echo "== CSS"
fresh; set_css '@import url("file:///etc/passwd");'; rejects "@import"
fresh; set_css '.a { background-image: url("https://example.invalid/x.png"); }'; rejects "url() to the network"
fresh; set_css '.a { background-image: url(file:///etc/shadow); }'; rejects "url() to another local file"
fresh; set_css '.a { background-image: url("resource:///org/gnome/shell/theme/../../x.svg"); }'; rejects "resource url with .."
fresh; set_css '.a { background-image: u\72l("file:///etc/passwd"); }'; rejects "escaped url()"
fresh; printf '.a { color: red; }\0 .b{}' >"$T_ROOT/data/theme.css"; rejects "NUL byte in CSS"
fresh; printf '.a { content: "\xff\xfe"; }' >"$T_ROOT/data/theme.css"; rejects "invalid UTF-8 in CSS"
fresh; set_css '.a { color: {{colors.primary.default.hex}}; }'; rejects "unrendered template"
fresh; set_css '/* a */ .a { color: red; } @IMPORT "x.css";'; rejects "@IMPORT in another case"
fresh; set_css '.a { background-image: url("file:///usr/local/share/m3e-gnome/gdm/background.png"); }'
check "the staged background url() is allowed" "${INGEST[@]}" check "$T_ROOT/data"

echo "== assets and configuration"
fresh; printf 'x' >"$T_ROOT/data/assets/icons/Googlebook/evil.sh"; rejects "asset with a script extension"
fresh; printf 'not a cursor' >"$T_ROOT/data/assets/icons/Googlebook/cursors/left_ptr"; rejects "cursor that is not Xcursor"
fresh; mkdir "$T_ROOT/data/assets/icons/.hidden"; printf '[Icon Theme]\n' >"$T_ROOT/data/assets/icons/.hidden/index.theme"; rejects "hidden theme directory"
fresh; printf '<svg xmlns:x="http://www.w3.org/1999/xlink"><image x:href="file:///etc/passwd"/></svg>' \
    >"$T_ROOT/data/assets/icons/Material-Symbols/symbolic/actions/go-next-symbolic.svg"; printf '<svg><image href="file:///etc/passwd"/></svg>' \
    >"$T_ROOT/data/assets/icons/Material-Symbols/symbolic/actions/go-next-symbolic.svg"; rejects "SVG with an external reference"
fresh; printf "icon_theme=Material-Symbols\ncursor_theme=x'; rm -rf /\nfont_name=a\nseed=image\n" >"$T_ROOT/data/greeter.conf"; rejects "quote in greeter.conf"
fresh; printf 'icon_theme=Material-Symbols\ncursor_theme=Googlebook\n' >"$T_ROOT/data/greeter.conf"; rejects "greeter.conf without font_name"

echo "== the helper never follows or runs what the user controls"
fresh
gdm_run apply --from "$T_ROOT/data" >/dev/null 2>&1
before="$(sha256sum "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource" | cut -d' ' -f1)"
printf '.evil { color: red; }\n' >"$T_ROOT/data/theme.css"; rm -f "$T_ROOT/data/background.png"
gdm_run refresh >/dev/null 2>&1
after="$(sha256sum "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource" | cut -d' ' -f1)"
check "editing the source directory after the install changes nothing (refresh uses the staged copy)" test "$before" = "$after"
check "the staged copy is root-controlled data in the state directory" test -f "$GR/var/lib/m3e-gnome/gdm/data/theme.css"
gdm_run restore --remove-helper >/dev/null 2>&1

echo "== test hooks and trust of the helper directory"
mkdir -p "$T_ROOT/fakeid"
# shellcheck disable=SC2016
printf '#!/bin/sh\n[ "$1" = "-u" ] && { echo 0; exit 0; }\nexec /usr/bin/id "$@"\n' >"$T_ROOT/fakeid/id"; chmod +x "$T_ROOT/fakeid/id"
HELPER_SRC="$GDM_SRC/m3e-gdm"
out="$(PATH="$T_ROOT/fakeid:$PATH" M3E_GDM_TEST=1 M3E_GDM_ROOT="$GR" bash "$HELPER_SRC" status 2>&1)"; rc=$?
check "as root, M3E_GDM_TEST/M3E_GDM_ROOT are refused" test "$rc" -ne 0
check "…with an explanation" grep -q 'refused when running as root\|must be owned by root' <<<"$out"
out="$(M3E_GDM_ROOT="$GR" bash "$HELPER_SRC" status 2>&1)"; rc=$?
check "M3E_GDM_ROOT without M3E_GDM_TEST=1 is refused" test "$rc" -ne 0
out="$(M3E_GDM_TEST=1 M3E_GDM_ROOT=/ bash "$HELPER_SRC" status 2>&1)"; rc=$?
check "M3E_GDM_ROOT=/ is refused" test "$rc" -ne 0
out="$(PATH="$T_ROOT/fakeid:$PATH" bash "$HELPER_SRC" status 2>&1)"; rc=$?
check "as root, a helper directory not owned by root is refused" test "$rc" -ne 0
check "…naming the ownership rule" grep -q 'owned by root' <<<"$out"
gdm_install_helper_into "$GR"
chmod 666 "$GR/usr/local/libexec/m3e-gnome/gdm/cmd.sh"
out="$(gdm_run status 2>&1)"; rc=$?
check "a world-writable helper file is refused" test "$rc" -ne 0
chmod 644 "$GR/usr/local/libexec/m3e-gnome/gdm/cmd.sh"
ln -s /etc/passwd "$GR/usr/local/libexec/m3e-gnome/gdm/extra.sh"
out="$(gdm_run status 2>&1)"; rc=$?
check "a symbolic link inside the helper directory is refused" test "$rc" -ne 0
rm -f "$GR/usr/local/libexec/m3e-gnome/gdm/extra.sh"

echo
if ((FAILS)); then echo "gdm input: $FAILS failure(s)"; exit 1; fi
echo "gdm input: all checks passed"
