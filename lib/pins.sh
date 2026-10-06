# shellcheck shell=bash
# Pinned upstream sources. Every git source is fetched at an exact commit (and verified), every download is checked
# against a sha256. Last re-checked 2026-10-05: all commits fetchable, all checksums match.
# A test or a packager may point M3E_PINS_FILE at a file that redefines these variables.

# GTK 3/4 + Shell base theme (GPL-3.0-or-later). Cloned at install time, never redistributed here.
MATGNOME_URL=https://github.com/SakibShahariar/material-gnome-theme.git
MATGNOME_REV=9dce9f6bbb17cd9eb545f7c6c994df4c945a8dc1      # 2026-09-28

# Papirus icon theme (GPL-3.0): coloured icons and folders; papirus-folders (MIT) recolours the folders.
PAPIRUS_URL=https://github.com/PapirusDevelopmentTeam/papirus-icon-theme.git
PAPIRUS_REV=bf539287ef5dc18529424a02cccee76175920a6f        # 2026-09-21
FOLDERS_URL=https://github.com/PapirusDevelopmentTeam/papirus-folders.git
FOLDERS_REV=0f838ee5679229e3a3e97e3b333c222c9e9615b4        # 2025-05-28

# Materia sound theme (GPL-3.0), built with meson into a staging directory.
MATERIA_URL=https://github.com/nana-4/materia-sound-theme.git
MATERIA_REV=10d30e9a01af4dec6a9cf94317c9536fec5a24f4        # 2020-05-30

# Companion GNOME Shell extensions.
# Pinned to the commit this version of the theme was tested with (update it at each release).
EXT_URL=https://github.com/maximeallanic/m3e-gnome-extensions.git
EXT_REV=3e75a439c018098d7cb93850561fcbbfb0b318bd

# Google Sans Flex (SIL OFL 1.1) from google/fonts.
GSF_BASE=https://raw.githubusercontent.com/google/fonts/a0e3dbcdc3a3ecfafff3f071159ae0221628922d/ofl/googlesansflex
GSF_FILE='GoogleSansFlex[GRAD,ROND,opsz,slnt,wdth,wght].ttf'
GSF_URL_NAME='GoogleSansFlex%5BGRAD%2CROND%2Copsz%2Cslnt%2Cwdth%2Cwght%5D.ttf'
GSF_SHA256=c31a482fbecbf2e07e6890134d20078723aadf732c9b9c6c9a44f86f8265b6fe
GSF_OFL_SHA256=fc13d69f63e36d284b6e383d4d1463d8ad404f0aa065e57cf961252d51063137

# matugen (GPL-2.0): template engine. Release binaries exist for x86_64 only; other architectures build from source
# (cargo install matugen --version "$MATUGEN_VERSION" --locked). Versions >= MATUGEN_MIN_VERSION (same major) are
# accepted when already installed.
MATUGEN_VERSION=4.2.0
MATUGEN_MIN_VERSION=4.2.0
MATUGEN_URL_X86_64=https://github.com/InioX/matugen/releases/download/v4.2.0/matugen-4.2.0-x86_64.tar.gz
MATUGEN_SHA256_X86_64=a2e3b50e49ed6439999ba3c252ed04fabd98ee4e9d12e5e5dff2e66370569751
