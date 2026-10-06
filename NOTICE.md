# Third-party notices

The code and original assets of this repository (installer, templates, stylesheets, scripts, tools, hand-drawn
icons) are released under the MIT License (see `LICENSE`). Everything below keeps its own license. The rule of the
installer is simple: **third-party code and data that is not Apache/MIT-compatible to embed is fetched at install
time from its upstream at a pinned commit and is never committed to this repository.**

## Fetched at install time (not redistributed here)

| Component | Upstream | License | How we use it |
|---|---|---|---|
| **Material-Gnome** (GTK 3/4 and Shell base theme) | <https://github.com/SakibShahariar/material-gnome-theme> | **GPL-3.0-or-later**, Copyright (C) 2026 Sakib Shahriar Shimanto (GitHub reports it as "Other"; the `LICENSE` file and the README at the pinned commit state GPL-3.0) | Cloned at the pinned commit `9dce9f6` into the cache and copied to `~/.themes/Material-Gnome`; its `LICENSE` is copied with it. The installer strips bold font weights from the installed GTK 4 stylesheets (a local modification, for the user's own use). Our stylesheets are separate files that are `@import`-ed after it. |
| **Papirus icon theme** | <https://github.com/PapirusDevelopmentTeam/papirus-icon-theme> | GPL-3.0 | Cloned at the pinned commit `bf53928`; `Papirus` and `Papirus-Dark` are copied to the user's icon directory. This repository only contains *symbolic links* to `Papirus-Dark` in `theme/icons/Material-Symbols`. |
| **papirus-folders** | <https://github.com/PapirusDevelopmentTeam/papirus-folders> | MIT, Copyright (c) 2017 Papirus Development Team | Cloned at `0f838ee`, installed to `~/.local/bin`; recolours the Papirus folders from the palette. |
| **Materia sound theme** | <https://github.com/nana-4/materia-sound-theme> | GPL-3.0; the sounds are Google's Material sound resources, **CC BY 4.0** (attribution: Google) | Cloned at `10d30e9`, built with meson into a staging directory, copied to `~/.local/share/sounds/Materia`. |
| **Google Sans Flex** | <https://github.com/google/fonts> (`ofl/googlesansflex`), Copyright 2015 The Google Sans Flex Authors | **SIL Open Font License 1.1** | Downloaded at the pinned commit `a0e3dbc` and checked against a sha256; installed with its `OFL.txt`. |
| **AOSP pointer drawables** | <https://android.googlesource.com/platform/frameworks/base> | Apache License 2.0, Copyright The Android Open Source Project | `tools/googlebook-cursors` downloads the vector drawables of the pinned commit, converts and renders them to Xcursor files in the user's icon directory. No AOSP file is stored here. |
| **Material Symbols** (build input) | <https://github.com/google/material-design-icons> | Apache License 2.0 | `tools/material-symbols` downloads symbols from a pinned commit when the icon theme is regenerated. |
| **matugen** | <https://github.com/InioX/matugen> | **GPL-2.0** (see the `LICENSE` of the project) | Release binary v4.2.0 (x86_64) downloaded from the project's GitHub release, checked against a sha256, installed to `~/.local/bin/matugen` unless a compatible one is already installed. It is run as a separate program (template renderer); nothing is linked or copied. |
| **@material/material-color-utilities** 0.4.0 | <https://github.com/material-foundation/material-color-utilities> | Apache License 2.0 | Installed with `npm ci` (versions pinned by `tools/material-palette/package-lock.json`) and bundled with esbuild (MIT) into `~/.local/lib/material-palette/palette.mjs` on the user's machine. |
| **m3e-gnome-extensions** | <https://github.com/maximeallanic/m3e-gnome-extensions> | MIT | The companion GNOME Shell extensions, fetched and built by the installer. |

### May we redistribute Material-Gnome?

Legally yes, under the GPL-3.0-or-later: a copy may be redistributed if it stays under the GPL with its notices
and source. We still do **not** vendor it, for two reasons: embedding GPL-3.0 files in an MIT repository would make
the combined work GPL-3.0 and blur the license of the original parts, and a pinned clone keeps the exact upstream
history and lets users read what they install. Nothing in this repository was copied from it. If a
future change copies parts of Material-Gnome into this repository, those files must carry the GPL-3.0 notice.

## Vendored in this repository

- **Material Symbols** glyph paths (`theme/icons/Material-Symbols/symbolic/**`): Apache License 2.0, Google. Generated
  by `tools/material-symbols` from the pinned upstream commit, then framed and renamed. The window-control icons are
  hand-drawn and covered by the MIT License.
- **Material 3 / Compose Material 3 tokens and motion values** (AndroidX, pinned commit
  `41edc910b2c7cf284c302543b435bfc7d2df1e49`, Apache License 2.0, Copyright The Android Open Source Project): numeric
  values used by the stylesheets and the spring table in `theme/motion`; each value cites its token.
- **Material 3 colour roles** are computed by Google's material-color-utilities (see above); this repository stores
  only the settings in `theme/matugen/palette.json`.

## Not included

- **GDM login-screen theming.** The previous private version of this installer rewrote the GDM theme with a script
  that ran as root and executed files from the user's home. That design lets any user-writable file run as root, so
  it is not part of this project. The login screen keeps the distribution's default theme.
- The Hanabi live wallpaper, Home Assistant and other personal integrations of the original setup.

## Trademarks

Material Design, Material You, Android, Pixel, Google and Google Sans are trademarks of Google LLC; GNOME is a
trademark of the GNOME Foundation; Papirus and the other names above belong to their owners. This project is not
affiliated with or endorsed by any of them.
