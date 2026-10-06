# shellcheck shell=bash
# Fixtures for every pinned source: small git repositories (fetched through the real pinned-fetch code path) and a
# font file with its checksum, plus the pins file that points the installer at them. Needs lib.sh.

make_fixtures() {
    local fix="$T_ROOT/fix" d sha
    mkdir -p "$fix"

    # Base GTK theme: matugen templates with real placeholders, and bold weights that the installer must strip.
    d="$fix/material-gnome"
    mkdir -p "$d"/{gtk-3.0,gtk-4.0,gnome-shell/assets,screenshots,.github}
    printf '@define-color primary {{colors.primary.default.hex}};\n' >"$d/gtk-3.0/colors-template.css"
    printf ':root {\n  --primary: {{colors.primary.default.hex}};\n}\n' >"$d/gtk-4.0/colors-template.css"
    printf '@define-color primary #000000;\n' >"$d/gtk-3.0/colors.css"
    printf ':root { --primary: #000000; }\n' >"$d/gtk-4.0/colors.css"
    printf '@import url("colors.css");\n' | tee "$d/gtk-3.0/gtk.css" "$d/gtk-3.0/gtk-dark.css" >/dev/null
    printf '@import url("colors.css");\n.title-1 { font-weight: bold; }\n.heading { font-weight: 700; }\n.x { font-weight: 400; }\n' |
        tee "$d/gtk-4.0/gtk.css" "$d/gtk-4.0/gtk-dark.css" >/dev/null
    printf '/* base */\n' >"$d/gnome-shell/gnome-shell.css"
    printf 'asset\n' >"$d/gnome-shell/assets/a.svg"
    printf '[Desktop Entry]\nName=Material-Gnome\n' >"$d/index.theme"
    printf 'GPL fixture\n' >"$d/LICENSE"
    printf 'png\n' >"$d/screenshots/s.png"
    printf 'ci\n' >"$d/.github/x"
    make_git_fixture "$d"
    MATGNOME_FIX_REV="$(git -C "$d" rev-parse HEAD)"

    # Papirus: just enough index.theme for papirus-symbolic.py.
    d="$fix/papirus"
    mkdir -p "$d/Papirus/16x16/apps" "$d/Papirus/16x16/symbolic/actions" "$d/Papirus-Dark"
    cat >"$d/Papirus/index.theme" <<'EOT'
[Icon Theme]
Name=Papirus
Inherits=hicolor
Directories=16x16/apps,16x16/symbolic/actions
ScaledDirectories=

[16x16/apps]
Context=Applications
Size=16
Type=Fixed

[16x16/symbolic/actions]
Context=Actions
Size=16
Type=Fixed
EOT
    cp "$d/Papirus/index.theme" "$d/Papirus-Dark/index.theme"
    printf '<svg/>\n' >"$d/Papirus/16x16/apps/a.svg"
    printf '<svg/>\n' >"$d/Papirus/16x16/symbolic/actions/b-symbolic.svg"
    make_git_fixture "$d"
    PAPIRUS_FIX_REV="$(git -C "$d" rev-parse HEAD)"

    # papirus-folders: a stub that records its arguments (the matugen hook calls it).
    d="$fix/papirus-folders"
    mkdir -p "$d"
    # shellcheck disable=SC2016  # literal $ for the generated stub
    printf '#!/bin/sh\necho "papirus-folders $*" >> "$HOME/.cache/papirus-folders.log"\n' >"$d/papirus-folders"
    chmod +x "$d/papirus-folders"
    make_git_fixture "$d"
    FOLDERS_FIX_REV="$(git -C "$d" rev-parse HEAD)"

    # Materia: a real meson project of the same shape as upstream.
    d="$fix/materia"
    mkdir -p "$d/material_product_sounds"
    printf "project('materia-sound-theme', version: '0.1', default_options: ['prefix=/usr'])\ntheme_dir = join_paths(get_option('datadir'), 'sounds', 'Materia')\ninstall_data('index.theme', install_dir: theme_dir)\nsubdir('material_product_sounds')\n" >"$d/meson.build"
    printf '[Sound Theme]\nName=Materia\nDirectories=stereo\n' >"$d/index.theme"
    printf "install_data('alert.ogg', rename: 'dialog-error.oga', install_dir: join_paths(theme_dir, 'stereo'))\n" >"$d/material_product_sounds/meson.build"
    printf 'ogg\n' >"$d/material_product_sounds/alert.ogg"
    make_git_fixture "$d"
    MATERIA_FIX_REV="$(git -C "$d" rev-parse HEAD)"

    # Companion extensions: the contract of scripts/install.sh --dest, nothing more.
    d="$fix/extensions"
    mkdir -p "$d/scripts" "$d"/extensions/{m3e-motion,m3e-extensions,status-bar}@maximeallanic.github.io
    cat >"$d/scripts/install.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
dest=''
while [[ $# -gt 0 ]]; do [[ "$1" == --dest ]] && { dest="$2"; shift; }; shift; done
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for u in "$root"/extensions/*/; do mkdir -p "$dest/$(basename "$u")"; cp -r "$u". "$dest/$(basename "$u")/"; done
EOT
    chmod +x "$d/scripts/install.sh"
    for u in m3e-motion m3e-extensions status-bar; do
        printf '{"uuid": "%s@maximeallanic.github.io", "name": "%s", "shell-version": ["50"]}\n' "$u" "$u" >"$d/extensions/$u@maximeallanic.github.io/metadata.json"
        printf '// %s\n' "$u" >"$d/extensions/$u@maximeallanic.github.io/extension.js"
    done
    make_git_fixture "$d"
    EXT_FIX_REV="$(git -C "$d" rev-parse HEAD)"

    # Font: random bytes are fine, the installer only checks the checksum.
    mkdir -p "$fix/font"
    head -c 2048 /dev/urandom >"$fix/font/font.ttf"
    printf 'SIL OFL fixture\n' >"$fix/font/OFL.txt"

    cat >"$T_ROOT/pins.sh" <<EOT
MATGNOME_URL=file://$fix/material-gnome
MATGNOME_REV=$MATGNOME_FIX_REV
PAPIRUS_URL=file://$fix/papirus
PAPIRUS_REV=$PAPIRUS_FIX_REV
FOLDERS_URL=file://$fix/papirus-folders
FOLDERS_REV=$FOLDERS_FIX_REV
MATERIA_URL=file://$fix/materia
MATERIA_REV=$MATERIA_FIX_REV
EXT_URL=file://$fix/extensions
EXT_REV=$EXT_FIX_REV
GSF_BASE=file://$fix/font
GSF_URL_NAME=font.ttf
GSF_SHA256=$(sha256sum "$fix/font/font.ttf" | cut -d' ' -f1)
GSF_OFL_SHA256=$(sha256sum "$fix/font/OFL.txt" | cut -d' ' -f1)
EOT
    export M3E_PINS_FILE="$T_ROOT/pins.sh"
}

# A wallpaper that material-sync can read (a tiny PNG written with the standard library).
make_wallpaper() { # path
    python3 - "$1" <<'PY'
import struct, sys, zlib
w = h = 8
raw = b"".join(b"\x00" + bytes([0x7B, 0x9F, 0x1C]) * w for _ in range(h))
def chunk(t, d):
    c = struct.pack(">I", len(d)) + t + d
    return c + struct.pack(">I", zlib.crc32(t + d))
open(sys.argv[1], "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                              + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
PY
}
