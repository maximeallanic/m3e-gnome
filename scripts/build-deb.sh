#!/usr/bin/env bash
# Build the Debian package m3e-gnome: the read-only runtime tree under /usr/share/m3e-gnome, three wrappers in
# /usr/bin, man pages and a bash completion. Installing it changes nothing in any home directory: the user runs
# m3e-gnome-install afterwards.
#
#   scripts/build-deb.sh VERSION [--out DIR] [--palette-bundle FILE]
#
# VERSION must equal M3E_VERSION in lib/common.sh ('-' becomes '~' in the Debian version). The palette bundle
# (tools/material-palette/dist/palette.mjs) is built with npm ci + esbuild, or taken from --palette-bundle (offline).
# Plain dpkg-deb, no debhelper: a file tree, three generated wrappers and three metadata files, nothing to compile.
# Result: DIR/m3e-gnome_<version>_all.deb (default DIR: dist/).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
die() { echo "error: $*" >&2; exit 1; }

out="$ROOT/dist" version="" bundle=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out) [[ $# -ge 2 ]] || die "--out needs a directory"; out="$2"; shift ;;
        --palette-bundle) [[ $# -ge 2 ]] || die "--palette-bundle needs a file"; bundle="$2"; shift ;;
        -h|--help) sed -n '2,/^# Result/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) die "unknown option: $1" ;;
        *) [[ -z "$version" ]] || die "one VERSION only"; version="$1" ;;
    esac
    shift
done
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || die "usage: build-deb.sh VERSION (like 0.1.0 or 0.2.0-rc1)"
command -v dpkg-deb >/dev/null || die "dpkg-deb is required (package dpkg)"
src_version="$(sed -n 's/^M3E_VERSION=//p' "$ROOT/lib/common.sh")"
[[ "$src_version" == "$version" ]] || die "VERSION $version differs from M3E_VERSION=$src_version in lib/common.sh"

pkg=m3e-gnome
debver="${version/-/\~}"
maintainer="Maxime Allanic <maximeallanic@users.noreply.github.com>"
epoch="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" log -1 --format=%ct 2>/dev/null || date +%s)}"

stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT
root="$stage/root"
tree="$root/usr/share/m3e-gnome"
doc="$root/usr/share/doc/$pkg"
mkdir -p "$tree" "$doc" "$root/usr/bin" "$root/DEBIAN" "$root/usr/share/man/man1" \
    "$root/usr/share/bash-completion/completions"

# Runtime tree: everything the scripts read, none of the development material (tests, dev/, screenshots/, node_modules).
cp -- "$ROOT/install.sh" "$ROOT/uninstall.sh" "$ROOT/verify.sh" "$ROOT/LICENSE" "$ROOT/NOTICE.md" "$ROOT/README.md" \
    "$ROOT/README.fr.md" "$ROOT/CHANGELOG.md" "$tree/"
for d in lib theme gdm docs tools; do cp -r -- "$ROOT/$d" "$tree/$d"; done
find "$tree" \( -name node_modules -o -name tests -o -name __pycache__ -o -name .test -o -name dist \) -prune -exec rm -rf -- {} +
mkdir -p "$tree/tools/material-palette/dist"
if [[ -n "$bundle" ]]; then
    install -m 644 -- "$bundle" "$tree/tools/material-palette/dist/palette.mjs"
else
    command -v npm >/dev/null || die "npm is required to build the palette bundle (or pass --palette-bundle FILE)"
    bash "$ROOT/tools/material-palette/build.sh" "$tree/tools/material-palette/dist/palette.mjs" >/dev/null
fi
[[ -s "$tree/tools/material-palette/dist/palette.mjs" ]] || die "empty palette bundle"

# Wrappers, man pages (from --help), completion.
summary_of() {
    case "$1" in
        install) echo "install the Material 3 Expressive theme for GNOME in your home directory" ;;
        uninstall) echo "remove what m3e-gnome-install installed and restore what it replaced" ;;
        verify) echo "check an m3e-gnome installation" ;;
    esac
}
for s in install uninstall verify; do
    name="m3e-gnome-$s"
    sed -e "s/@NAME@/$name/g" -e "s/@SCRIPT@/$s.sh/g" "$ROOT/packaging/wrapper.sh" > "$root/usr/bin/$name"
    chmod 755 "$root/usr/bin/$name"
    bash "$ROOT/$s.sh" --help 2>&1 | python3 "$ROOT/packaging/mkman.py" "$name" "$version" "$(summary_of "$s")" \
        | gzip -9n > "$root/usr/share/man/man1/$name.1.gz"
done
install -m 644 -- "$ROOT/packaging/m3e-gnome.bash" "$root/usr/share/bash-completion/completions/m3e-gnome-install"
for s in uninstall verify; do
    ln -s m3e-gnome-install "$root/usr/share/bash-completion/completions/m3e-gnome-$s"
done

# Documentation and Debian metadata.
cp -- "$ROOT/README.md" "$ROOT/NOTICE.md" "$doc/"
rfc_date="$(date -u -d "@$epoch" '+%a, %d %b %Y %H:%M:%S +0000')"
{
    printf '%s (%s) unstable; urgency=medium\n\n' "$pkg" "$debver"
    printf '  * Release %s. See /usr/share/m3e-gnome/CHANGELOG.md for the full list of changes.\n\n' "$version"
    printf ' -- %s  %s\n' "$maintainer" "$rfc_date"
} | gzip -9n > "$doc/changelog.gz"
{
    cat <<'HEAD'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: m3e-gnome
Upstream-Contact: Maxime Allanic <maximeallanic@users.noreply.github.com>
Source: https://github.com/maximeallanic/m3e-gnome
Comment: Third-party themes, fonts, icons and tools that the installer downloads
 at install time (Material-Gnome, Papirus, Materia, Google Sans Flex, matugen)
 are not part of this package; their licenses are listed in NOTICE.md.

Files: *
Copyright: 2026 Maxime Allanic
License: MIT

Files: usr/share/m3e-gnome/theme/icons/Material-Symbols/symbolic/*
Copyright: Google LLC
License: Apache-2.0
Comment: Glyph paths generated from Material Symbols (google/material-design-icons) at a pinned commit.
 The window-control icons are hand-drawn and covered by the MIT License.

Files: usr/share/m3e-gnome/tools/material-palette/dist/palette.mjs
Copyright: Google LLC
License: Apache-2.0
Comment: Bundle of @material/material-color-utilities 0.4.0 (Apache-2.0) made with esbuild (MIT).

Files: usr/share/m3e-gnome/theme/motion/*
Copyright: The Android Open Source Project
License: Apache-2.0
Comment: Numeric values of Material 3 and Android motion tokens; see NOTICE.md for the exact sources.

License: Apache-2.0
 Licensed under the Apache License, Version 2.0. On Debian systems the full
 text is in /usr/share/common-licenses/Apache-2.0.

License: MIT
HEAD
    sed -n '5,$p' "$ROOT/LICENSE" | sed -e 's/^$/./' -e 's/^/ /'
} > "$doc/copyright"

cat > "$root/DEBIAN/control" <<CONTROL
Package: $pkg
Version: $debver
Architecture: all
Maintainer: $maintainer
Depends: python3 (>= 3.9), rsync, curl, git, nodejs, libglib2.0-bin, dconf-cli, fontconfig
Recommends: ffmpeg, librsvg2-bin, meson, ninja-build, libgtk-3-bin, gnome-shell-extension-user-theme, gnome-shell-extension-m3e
Suggests: gnome-shell
Section: gnome
Priority: optional
Homepage: https://github.com/maximeallanic/m3e-gnome
Description: Material 3 Expressive theme for GNOME (installer run as your user)
 Installs nothing into your home directory by itself. It ships the installer
 of the m3e-gnome theme (GTK 3/4, libadwaita, Chrome, GNOME Shell, icons,
 cursor, sounds, font, palette computed from your wallpaper) and the commands
 m3e-gnome-install, m3e-gnome-uninstall and m3e-gnome-verify. Run
 m3e-gnome-install as your own user: it downloads some pinned sources
 (themes, icons, font) at that time, so it needs network access.
 .
 The optional login-screen theming is opt-in: m3e-gnome-install --gdm.
CONTROL
cat > "$root/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    echo "m3e-gnome is installed but no theme is applied yet. As your own user (not root), from your GNOME session:"
    echo "  m3e-gnome-install --dry-run   # see what it would do"
    echo "  m3e-gnome-install             # install (needs network access for the pinned sources)"
    echo "  m3e-gnome-verify              # check, after logging out and in again"
    echo "Undo with m3e-gnome-uninstall. Removing this package does not touch your home directory."
fi
exit 0
POSTINST
chmod 755 "$root/DEBIAN/postinst"

# Modes: executables 755, everything else 644, directories 755; then timestamps; then the installed size.
find "$root" -type d -exec chmod 755 {} +
find "$root" -type f -perm /111 -exec chmod 755 {} +
find "$root" -type f ! -perm /111 -exec chmod 644 {} +
find "$root" -exec touch -h -d "@$epoch" {} +
size_kb="$(du -sk --apparent-size "$root" --exclude=DEBIAN | cut -f1)"
sed -i "s/^Architecture: all$/&\nInstalled-Size: $size_kb/" "$root/DEBIAN/control"

mkdir -p "$out"
deb="$out/${pkg}_${debver}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$root" "$deb" >/dev/null
echo "built $deb"
