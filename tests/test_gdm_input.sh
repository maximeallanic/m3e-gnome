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
    if ((rc == 0)); then gdm_run restore >/dev/null 2>&1; fi   # keep one accepted case from poisoning the next ones
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

# Structure of every chunk, not just the header: a PNG that passes a 33-byte check can still be a trap for the decoder.
png_edit() { # python snippet operating on bytes variable d, written back to the background
    python3 - "$T_ROOT/data/background.png" "$1" <<'PY'
import struct, sys, zlib
path, code = sys.argv[1], sys.argv[2]
d = open(path, "rb").read()
def chunk(t, data):
    return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
exec(code)
open(path, "wb").write(d)
PY
}
fresh; png_edit 'i = d.index(b"IDAT"); d = d[:i + 6] + bytes([d[i + 6] ^ 0xFF]) + d[i + 7:]'; rejects "PNG with a corrupted IDAT chunk (CRC)"
fresh; png_edit 'd = d + b"trailing bytes"'; rejects "PNG with trailing data after IEND"
fresh; png_edit 'a = d.index(b"IDAT") - 4; b = d.index(b"IEND") - 4; d = d[:a] + d[b:]'; rejects "PNG without IDAT"
fresh; png_edit 'a = d.index(b"IEND") - 4; d = d[:a] + chunk(b"tEXt", b"k\0v") + d[a:]'
check "an ancillary chunk before IEND is fine" "${INGEST[@]}" check "$T_ROOT/data"
fresh; png_edit 'i = d.index(b"IDAT") - 4; d = d[:i] + struct.pack(">I", 0x7FFFFFF0) + d[i + 4:]'; rejects "chunk length beyond the file"
fresh; gdm_make_png "$T_ROOT/data/background.png" 5000 3000; rejects "PNG larger than 4096x2304"
fresh; gdm_make_png "$T_ROOT/data/background.png" 1920 540
check "a 1920 px wide blur is fine" "${INGEST[@]}" check "$T_ROOT/data"
fresh; python3 - "$T_ROOT/data/assets/icons/Googlebook/big.png" <<'PY'
import struct, sys, zlib
w = h = 3000
def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
open(sys.argv[1], "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\0" * 64)) + chunk(b"IEND", b""))
PY
rejects "an icon PNG of 3000x3000 (decompression-bomb size)"

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
# Comment markers hidden inside two string literals: a regex that strips comments first deletes the span between them and
# the url()/@import in the middle bypasses the allow-list, while a real CSS parser sees them.
fresh; set_css '.a { content: "/*"; background-image: url(file:///etc/passwd); content: "*/"; }'; rejects "url() hidden between comment markers in strings"
fresh; set_css '.a { content: "/*"; } @import "file:///tmp/evil.css"; .b { content: "*/"; }'; rejects "@import hidden between comment markers in strings"
fresh; set_css '.a { background-image: URL( "file:///etc/passwd" ); }'; rejects "uppercase url with whitespace"
fresh; set_css '.a { background-image: url ( file:///etc/passwd ); }'; rejects "url with a space before the parenthesis"
fresh; set_css '.a { background-image: url(resource:///org/gnome/shell/theme/a.svg) ; background: url(http://x.invalid/a.png); }'; rejects "second url() after an allowed one"
fresh; set_css '.a { background-image: image-set("file:///etc/passwd" 1x); }'; rejects "image-set()"
fresh; set_css '.a { background-image: -webkit-image-set(url(file:///etc/passwd) 1x); }'; rejects "prefixed image-set()"
fresh; set_css '@ImPoRt "x.css";'; rejects "@import in mixed case"
fresh; set_css '@import/**/"x.css";'; rejects "@import glued to a comment"
fresh; set_css '@media screen { .a { color: red; } }'; rejects "any at-rule"
fresh; set_css '.a { color: red; '; rejects "unbalanced brace (open)"
fresh; set_css '.a { color: red; } }'; rejects "unbalanced brace (close)"
fresh; set_css '.a { color: rgba(1,2,3; }'; rejects "unbalanced parenthesis"
fresh; set_css '.a { content: "unterminated; }'; rejects "unterminated string"
fresh; set_css '.a { color: red; } /* unterminated comment'; rejects "unterminated comment"
fresh; set_css '.a { content: "a\
b"; }'; rejects "backslash line continuation in a string"
fresh; set_css '.a { color: red; } @\69mport "x.css";'; rejects "escaped at-rule name"
fresh; set_css '.a { background-image: url(resource:///org/gnome/shell/theme/a.svg)x; }'; rejects "garbage glued to a url token"
fresh; set_css '/* a "quote */ .a { color: red; } /* another " */'
check "quotes inside comments are fine" "${INGEST[@]}" check "$T_ROOT/data"
fresh; set_css '.a { background-image: url(file:///usr/local/share/m3e-gnome/gdm/background.png); }'
check "the staged background url() is allowed" "${INGEST[@]}" check "$T_ROOT/data"

echo "== assets and configuration"
fresh; printf 'x' >"$T_ROOT/data/assets/icons/Googlebook/evil.sh"; rejects "asset with a script extension"
fresh; printf 'not a cursor' >"$T_ROOT/data/assets/icons/Googlebook/cursors/left_ptr"; rejects "cursor that is not Xcursor"
fresh; mkdir "$T_ROOT/data/assets/icons/.hidden"; printf '[Icon Theme]\n' >"$T_ROOT/data/assets/icons/.hidden/index.theme"; rejects "hidden theme directory"
fresh; printf '<svg xmlns:x="http://www.w3.org/1999/xlink"><image x:href="file:///etc/passwd"/></svg>' \
    >"$T_ROOT/data/assets/icons/Material-Symbols/symbolic/actions/go-next-symbolic.svg"; printf '<svg><image href="file:///etc/passwd"/></svg>' \
    >"$T_ROOT/data/assets/icons/Material-Symbols/symbolic/actions/go-next-symbolic.svg"; rejects "SVG with an external reference"
# Theme directory names are an allow-list: the greeter must not be handed a replacement for the system's default themes.
for n in default hicolor Adwaita Papirus Yaru; do
    fresh; cp -r "$T_ROOT/data/assets/icons/Googlebook" "$T_ROOT/data/assets/icons/$n"; rejects "asset theme named $n"
done
fresh; cp -r "$T_ROOT/data/assets/fonts/GoogleSansFlex" "$T_ROOT/data/assets/fonts/DejaVu"; rejects "font directory with a name outside the set"
fresh; rm -rf "$T_ROOT/data/assets/icons/Googlebook"; cp -r "$T_ROOT/data/assets/icons/Material-Symbols" "$T_ROOT/data/assets/icons/Googlebook-White"
check "Googlebook-White is in the set" "${INGEST[@]}" check "$T_ROOT/data"
fresh; printf "icon_theme=Material-Symbols\ncursor_theme=x'; rm -rf /\nfont_name=a\nseed=image\n" >"$T_ROOT/data/greeter.conf"; rejects "quote in greeter.conf"
fresh; printf 'icon_theme=Material-Symbols\ncursor_theme=Googlebook\n' >"$T_ROOT/data/greeter.conf"; rejects "greeter.conf without font_name"

echo "== the helper never follows or runs what the user controls"
fresh
gdm_ok apply --from "$T_ROOT/data"
before="$(sha256sum "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource" | cut -d' ' -f1)"
printf '.evil { color: red; }\n' >"$T_ROOT/data/theme.css"; rm -f "$T_ROOT/data/background.png"
gdm_ok refresh
after="$(sha256sum "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource" | cut -d' ' -f1)"
check "editing the source directory after the install changes nothing (refresh uses the staged copy)" test "$before" = "$after"
check "the staged copy is root-controlled data in the state directory" test -f "$GR/var/lib/m3e-gnome/gdm/data/theme.css"
gdm_ok restore --remove-helper

echo "== test hooks and trust of the helper directory"
mkdir -p "$T_ROOT/fakeid"
HELPER_SRC="$GDM_SRC/m3e-gdm"
# "Really root" is emulated with fakeroot (bash's own $EUID is 0 under it; files keep their real owner, which is not root).
if command -v fakeroot >/dev/null 2>&1; then
    out="$(M3E_GDM_TEST=1 M3E_GDM_ROOT="$GR" fakeroot -- bash "$HELPER_SRC" status 2>&1)"; rc=$?
    check "as root, the helper refuses to run from a directory that root does not own" test "$rc" -ne 0
    check "…naming the ownership rule" grep -q 'owned by root' <<<"$out"
else
    echo "  skipped: fakeroot not installed"
fi
out="$(M3E_GDM_ROOT="$GR" bash "$HELPER_SRC" status 2>&1)"; rc=$?
check "M3E_GDM_ROOT without M3E_GDM_TEST=1 is refused" test "$rc" -ne 0
out="$(M3E_GDM_TEST=1 M3E_GDM_ROOT=/ bash "$HELPER_SRC" status 2>&1)"; rc=$?
check "M3E_GDM_ROOT=/ is refused" test "$rc" -ne 0
gdm_install_helper_into "$GR"
chmod 666 "$GR/usr/local/libexec/m3e-gnome/gdm/cmd.sh"
out="$(gdm_run status 2>&1)"; rc=$?
check "a world-writable helper file is refused" test "$rc" -ne 0
chmod 644 "$GR/usr/local/libexec/m3e-gnome/gdm/cmd.sh"
ln -s /etc/passwd "$GR/usr/local/libexec/m3e-gnome/gdm/extra.sh"
out="$(gdm_run status 2>&1)"; rc=$?
check "a symbolic link inside the helper directory is refused" test "$rc" -ne 0
rm -f "$GR/usr/local/libexec/m3e-gnome/gdm/extra.sh"

echo "== environment hardening and ancestors"
# A directory above the helper that others can write lets them swap the whole helper directory.
chmod 775 "$GR/usr/local/libexec"
out="$(gdm_run status 2>&1)"; rc=$?
check "a group-writable ancestor of the helper directory is refused" test "$rc" -ne 0
check "…naming the ancestor" grep -q 'ancestor' <<<"$out"
chmod 755 "$GR/usr/local/libexec"
check "back to normal, the helper runs again" gdm_run status

# The installer applies the same rule to the destination before it runs `sudo install` there.
anc="$T_ROOT/anc"; mkdir -p "$anc/a/b"; chmod 755 "$anc" "$anc/a" "$anc/a/b"
ancestors_ok() { ( source "$REPO/lib/common.sh"; source "$REPO/lib/gdm.sh"; gdm_ancestors_ok "$1" "$(id -u)" "$anc" ); }
check "installer: root-owned (here: own) non-writable ancestors are accepted" ancestors_ok "$anc/a/b/c/d"
chmod 775 "$anc/a"
check_not "installer: a group-writable ancestor of the destination is refused" ancestors_ok "$anc/a/b/c/d"
chmod 755 "$anc/a"

# Reverse test: with a lying `id` and the test hooks set, a process that REALLY is root (fakeroot) must not enter test
# mode. The old code asked `id -u`; the decision must come from bash's own $EUID.
if command -v fakeroot >/dev/null 2>&1; then
    # shellcheck disable=SC2016
    printf '#!/bin/sh\n[ "$1" = "-u" ] && { echo 1000; exit 0; }\nexec /usr/bin/id "$@"\n' >"$T_ROOT/fakeid/id"; chmod +x "$T_ROOT/fakeid/id"
    out="$(PATH="$T_ROOT/fakeid:$PATH" M3E_GDM_TEST=1 M3E_GDM_ROOT="$GR" fakeroot -- bash "$GR/usr/local/libexec/m3e-gnome/gdm/m3e-gdm" status 2>&1)"; rc=$?
    check "as real root (fakeroot) with a lying id and test hooks set, the helper refuses" test "$rc" -ne 0
    check "…it did not report a state (test mode was not entered)" bash -c "! grep -q 'installed:' <<<'$out'"
else
    echo "  skipped: fakeroot not installed"
fi

# The environment purge keeps PATH and nothing else of what a caller can set (library, module and config search paths
# of the tools root spawns: glib, gdk-pixbuf, fontconfig, python, dpkg, dconf ...).
purged="$(env -i PATH=/usr/bin:/bin GIO_EXTRA_MODULES=/tmp/x GIO_MODULE_DIR=/tmp/x GDK_PIXBUF_MODULE_FILE=/tmp/x FONTCONFIG_FILE=/tmp/x \
    GTK_PATH=/tmp/x GSETTINGS_SCHEMA_DIR=/tmp/x G_MESSAGES_DEBUG=all LD_PRELOAD=/tmp/x PYTHONPATH=/tmp/x DPKG_ADMINDIR=/tmp/x \
    DCONF_PROFILE=/tmp/x HOME=/tmp/x TMPDIR=/tmp/x BASH_ENV=/tmp/x bash -c "source '$GDM_SRC/common.sh'; sanitize_env; env" 2>/dev/null)"
check "sanitize_env drops every variable except PATH and the C locale" bash -c "! grep -qE '^(GIO_|GDK_|FONTCONFIG|GTK_|GSETTINGS|G_|LD_|PYTHON|DPKG|DCONF|HOME|TMPDIR|BASH_ENV)' <<<'$purged'"
check "…and sets a fixed PATH and the C locale" bash -c "grep -qx 'PATH=/usr/sbin:/usr/bin:/sbin:/bin' <<<'$purged' && grep -qx 'LC_ALL=C' <<<'$purged'"

echo
if ((FAILS)); then echo "gdm input: $FAILS failure(s)"; exit 1; fi
echo "gdm input: all checks passed"
