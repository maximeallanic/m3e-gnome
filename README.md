# m3e-gnome

[![CI](https://github.com/maximeallanic/m3e-gnome/actions/workflows/ci.yml/badge.svg)](https://github.com/maximeallanic/m3e-gnome/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GNOME 50](https://img.shields.io/badge/GNOME-50-4a86cf.svg)](docs/compatibility.md)

English | [Francais](README.fr.md)

A Material 3 Expressive (M3E) look for GNOME 50. The colour palette is computed from your wallpaper the way
Android's Material You does it, and it is applied to GTK 3, GTK 4 / libadwaita, GNOME Shell, icons, the cursor, the
sounds and the font. Three companion Shell extensions add the motion and a few Android-style details that CSS cannot
do.

<!-- screenshots:start -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="screenshots/desktop-light.png">
    <img src="screenshots/desktop-dark.png" width="880" alt="M3E-themed GNOME desktop: Settings, Files and a terminal over a generated wallpaper">
  </picture>
</p>

<table>
  <tr><th>Dark</th><th>Light</th></tr>
  <tr><td colspan="2" align="center">Overview</td></tr>
  <tr>
    <td><img src="screenshots/overview-dark.png" width="440" alt="Overview, dark"></td>
    <td><img src="screenshots/overview-light.png" width="440" alt="Overview, light"></td>
  </tr>
  <tr><td colspan="2" align="center">Quick settings</td></tr>
  <tr>
    <td><img src="screenshots/quick-settings-dark.png" width="440" alt="Quick settings, dark"></td>
    <td><img src="screenshots/quick-settings-light.png" width="440" alt="Quick settings, light"></td>
  </tr>
  <tr><td colspan="2" align="center">Notifications and calendar</td></tr>
  <tr>
    <td><img src="screenshots/notifications-dark.png" width="440" alt="Notifications and calendar, dark"></td>
    <td><img src="screenshots/calendar-light.png" width="440" alt="Notifications and calendar, light"></td>
  </tr>
  <tr><td colspan="2" align="center">App grid</td></tr>
  <tr>
    <td><img src="screenshots/app-grid-dark.png" width="440" alt="App grid, dark"></td>
    <td><img src="screenshots/app-grid-light.png" width="440" alt="App grid, light"></td>
  </tr>
  <tr><td colspan="2" align="center">Settings, GTK 4 / libadwaita</td></tr>
  <tr>
    <td><img src="screenshots/settings-gtk4-dark.png" width="440" alt="Settings (GTK 4), dark"></td>
    <td><img src="screenshots/settings-gtk4-light.png" width="440" alt="Settings (GTK 4), light"></td>
  </tr>
  <tr><td colspan="2" align="center">Files, GTK 4 / libadwaita</td></tr>
  <tr>
    <td><img src="screenshots/files-gtk4-dark.png" width="440" alt="Files (GTK 4), dark"></td>
    <td><img src="screenshots/files-gtk4-light.png" width="440" alt="Files (GTK 4), light"></td>
  </tr>
  <tr><td colspan="2" align="center">Terminal</td></tr>
  <tr>
    <td><img src="screenshots/terminal-dark.png" width="440" alt="Terminal, dark"></td>
    <td><img src="screenshots/terminal-light.png" width="440" alt="Terminal, light"></td>
  </tr>
  <tr><td colspan="2" align="center">Dialogs</td></tr>
  <tr>
    <td><img src="screenshots/dialogs-dark.png" width="440" alt="Modal dialog, dark"></td>
    <td><img src="screenshots/dialogs-light.png" width="440" alt="Modal dialog, light"></td>
  </tr>
  <tr><td colspan="2" align="center">Status bar (Android style, with the battery pill) and quick settings</td></tr>
  <tr>
    <td><img src="screenshots/status-bar-dark.png" width="440" alt="Status bar, dark"></td>
    <td><img src="screenshots/status-bar-light.png" width="440" alt="Status bar, light"></td>
  </tr>
</table>

<p align="center">
  <img src="screenshots/login-dark.png" width="440" alt="GDM login screen (password prompt), dark, rendered by a nested Shell in gdm mode">
  <br><sub>Opt-in GDM login screen, see <a href="docs/gdm.md">docs/gdm.md</a> (flat background: no wallpaper in the capture).</sub>
</p>

<p align="center">
  <img src="screenshots/alt-tab-dark.png" width="440" alt="Alt+Tab window switcher">
</p>

<p align="center">
  <img src="screenshots/palette-from-wallpaper.png" width="880" alt="Four generated wallpapers, the desktop and the palette derived from each">
</p>

All screenshots come from a nested, headless GNOME Shell with demo data and generated (CC0) wallpapers; see [screenshots/README.md](screenshots/README.md) for how to regenerate them.
<!-- screenshots:end -->

## Why

GNOME's stock look is neutral and the accent colour is one of a few presets. If you like how Android 16 and later
looks and moves (tinted surfaces, pill-shaped controls, springs instead of fixed-duration easing) and want it on
the desktop, this project does that without recompiling mutter or GNOME Shell: it is CSS, templates, a few scripts and
Shell extensions, all under your home directory.

It is for people who run GNOME 50 and are comfortable with a theme that follows the wallpaper, replaces the icon theme,
the cursor, the sound theme and the interface font, and changes how the Shell animates. Everything the installer
changes is recorded, and `./uninstall.sh` puts it back.

## Features

- **Palette from the wallpaper.** Seed colour extracted like Android's `WallpaperColors`, roles computed with
  Google's [material-color-utilities](https://github.com/material-foundation/material-color-utilities) (2025 colour
  spec, tonal-spot, phone platform), rendered into the themes by [matugen](https://github.com/InioX/matugen). It
  updates when the wallpaper or the dark/light setting changes.
- **GTK 3, GTK 4 and libadwaita.** [Material-Gnome](https://github.com/SakibShahariar/material-gnome-theme) as the
  base, plus M3E components on top: buttons, switches (with icons in the thumb), sliders, scrollbars, tabs, lists,
  menus, dialogs, text fields, and a single title-bar geometry (40 px bar, 30 px round buttons).
- **GNOME Shell.** One generated stylesheet (`M3E-Shell`) covering the top bar, menus, quick settings, calendar,
  notifications, overview, app grid, dialogs, OSD, lock screen, screenshot UI and on-screen keyboard.
- **Icons.** `Material-Symbols` symbolic icon theme built from Material Symbols, falling back to Papirus (colour app
  icons, folder colour matched to the palette).
- **Cursor.** Googlebook pointers from AOSP, built as Xcursor files, black (default) or white.
- **Sounds and font.** Materia sound theme; Google Sans Flex as interface font.
- **Motion.** Spring-based M3E animations for the Shell and windows, from the
  [m3e-gnome-extensions](https://github.com/maximeallanic/m3e-gnome-extensions) companion.
- **No bold anywhere.** A deliberate rule of this theme (see [design notes](docs/design-notes.md)).
- **Reversible.** Every file and setting the installer touches is recorded and backed up.

## Requirements and compatibility

| | Status |
|---|---|
| GNOME Shell 50 (validated on 50.5) | Verified |
| Other GNOME versions | The installer warns and continues; untested |
| Wayland | Verified (nested headless Shell for benches; the author's daily session) |
| X11 session | Untested. The CSS includes rules for mutter X11 title-bar frames, but no X11 session was verified |
| Debian | Verified (the installer round trip was run for real on Debian) |
| Ubuntu | Same package names as Debian; untested |
| Fedora, Arch, openSUSE | Package names checked as text only; untested |
| CPU architecture | x86_64 for the bundled matugen download; other architectures must build matugen themselves |

You also need the GNOME **User Themes** extension (needed to load a Shell theme), Python 3.9 or newer, Node.js and
npm (for the palette bundle), and a few common tools. `./install.sh` checks for them and prints the exact command for
your distribution. Details: [docs/installation.md](docs/installation.md) and [docs/compatibility.md](docs/compatibility.md).

Only the default XDG layout is supported (`~/.config`, `~/.cache`, `~/.local/share`).

## Install

Run it from your GNOME session (it needs `gsettings`/dconf and a session bus), as your user, without `sudo`:

```sh
git clone https://github.com/maximeallanic/m3e-gnome
cd m3e-gnome
./install.sh --dry-run        # print what would be done, change nothing
./install.sh                  # install
```

Then **log out and back in**: the Shell, the extensions and GTK applications load the theme at login. Finally run
`./verify.sh`.

### From a release

The [releases page](https://github.com/maximeallanic/m3e-gnome/releases) has a Debian package and a source tarball
(check them with `sha256sum -c SHA256SUMS`). Both still run the same installer, as your user, and still download the
pinned sources when you run it (network needed); the package itself changes nothing in your home directory.

```sh
# Debian/Ubuntu: installs /usr/share/m3e-gnome and the commands m3e-gnome-install, -uninstall and -verify
sudo apt install ./m3e-gnome_<version>_all.deb
m3e-gnome-install --dry-run && m3e-gnome-install
# any distribution: the tarball is the same tree as the git checkout
tar xzf m3e-gnome-<version>.tar.gz && cd m3e-gnome-<version> && ./install.sh --dry-run && ./install.sh
```

If the package `gnome-shell-extension-m3e` (from the m3e-gnome-extensions releases) is installed, the installer enables
those system-wide extensions instead of downloading them. Removing the `.deb` does not undo the theme: run
`m3e-gnome-uninstall` first. The `.deb` has only been checked by unpacking it, not installed with `dpkg` on a live system.

If the Shell theme does not load, install the User Themes extension and run `./install.sh` again. Missing system
packages: `./install.sh --install-deps` runs your package manager with `sudo` after showing the command and asking.

| Option | Effect |
|---|---|
| `--dry-run` | Print the actions, change nothing |
| `-y`, `--yes` | Do not ask for confirmation |
| `--install-deps` | Install missing system packages with `sudo` (asks first) |
| `--dark` / `--light` | Colour scheme to set (default `--dark`); `--keep-color-scheme` leaves it unchanged |
| `--cursor black\|white` | Cursor variant (default `black`) |
| `--no-extensions` | Do not install the companion Shell extensions |
| `--extensions-only` | Install only the companion extensions |
| `--extensions-dir DIR` | Use a local `m3e-gnome-extensions` checkout instead of fetching it |
| `--skip STEP` | Skip a step, repeatable: `gtk-theme icons cursor sounds font palette extensions` |
| `--gdm` | **Opt-in**: also theme the GDM login screen. Uses `sudo` for that step only, after printing the exact plan. See [docs/gdm.md](docs/gdm.md) |
| `--gdm-only` | Only the GDM step (after a full install) |
| `--gdm-image FILE` | Seed colour and blurred background of the login screen (default: your dark wallpaper) |
| `--gdm-force` | Let the GDM helper run on a GNOME Shell major it was not verified with |
| `--no-session-check` | Do not require a running GNOME session (packaging, tests) |
| `--uninstall` | Same as `./uninstall.sh` |
| `--version`, `-h`, `--help` | |

## What gets installed, and where

| What | Where |
|---|---|
| Base GTK theme (Material-Gnome, bold weights removed from its GTK 4 CSS) | `~/.themes/Material-Gnome` |
| Shell theme (generated) | `~/.themes/M3E-Shell` |
| M3E stylesheets and templates | `~/.config/m3e-gnome/` |
| GTK entry points | `~/.config/gtk-3.0/gtk.css`, `~/.config/gtk-4.0/{gtk.css,gtk-dark.css,colors.css}` |
| Icons: `Material-Symbols`, `Papirus`, `Papirus-Dark`, `Papirus-Symbolic` | `~/.local/share/icons/` |
| Cursor: `Googlebook` or `Googlebook-White` (also `~/.icons/default`) | `~/.local/share/icons/` |
| Sounds (`Materia`), font (Google Sans Flex) | `~/.local/share/sounds/`, `~/.local/share/fonts/` |
| Palette scripts and matugen (if missing) | `~/.local/bin/`, `~/.local/lib/material-palette/` |
| Palette service | `~/.config/systemd/user/material-sync.service` |
| Companion extensions | `~/.local/share/gnome-shell/extensions/` |
| Record of owned paths, backups, `restore.sh` | `~/.local/share/m3e-gnome/{manifest,backup/<timestamp>/}` |
| Download cache | `~/.cache/m3e-gnome/` |

It also sets GNOME settings (GTK, icon, cursor, sound and Shell theme names, fonts, button layout, colour scheme,
User Themes, extensions) and the Ptyxis palette if Ptyxis is installed. Old values are backed up first.
See [docs/architecture.md](docs/architecture.md).

## How the colours follow the wallpaper

A user service (`material-sync.service`) watches the wallpaper, the colour scheme and the enabled extensions through
`dconf watch`. After a change it picks the source image (GNOME wallpaper: `picture-uri-dark` in dark mode,
`picture-uri` in light mode), computes the palette, renders every template with matugen, reloads the Shell and GTK
themes, and sets the nearest GNOME accent and Papirus folder colour. GTK 4 applications and Chrome pick up new colours
when they are restarted. Customisation: [docs/customization.md](docs/customization.md).

## Update

```sh
cd m3e-gnome
git pull
./install.sh        # idempotent: reinstalls what changed
```

Third-party sources are pinned to exact commits or checksums in `lib/pins.sh`, so a pull is what moves them forward.

## Uninstall and restore

```sh
./uninstall.sh --dry-run
./uninstall.sh
```

This removes only the paths recorded in `~/.local/share/m3e-gnome/manifest` (never by pattern), puts back the files
that were replaced and the old GNOME settings from `~/.local/share/m3e-gnome/backup/<timestamp>/`, then asks you to log
out and in. Details: [docs/troubleshooting.md](docs/troubleshooting.md).

## Known limitations

- **Chrome** needs *Settings > Appearance > Theme: GTK* to use the theme, and it keeps a dark toolbar and active tab
  in light mode (see [compatibility](docs/compatibility.md)).
- **Qt applications and libdecor windows** are not themed by the GTK CSS: Qt decorations do not follow it, and
  libdecor and mutter X11 frames draw their own shadows (square bottom corners).
- **GDM login screen: opt-in, Debian-family verified only.** `./install.sh --gdm` themes it through a root helper that
  treats everything the installer prepares as untrusted data (see [docs/gdm.md](docs/gdm.md) for the security model).
  Verified in a fake system root and by a nested Shell on Debian; not yet tried on a real boot of other distributions.
  The login screen follows the stylesheet only, not your wallpaper colours live: it is frozen at install time.
- **Flatpak applications:** nothing in the installer gives sandboxed applications access to the theme or the user
  stylesheets. Untested.
- Validated on GNOME 50.5 only; the extensions patch private Shell classes.
- Libadwaita animations that are hard-coded in the library cannot be restyled in CSS.
- A few Shell surfaces are approximations because St (the Shell's toolkit) cannot express the Material shape.

Full list: [docs/compatibility.md](docs/compatibility.md), [docs/troubleshooting.md](docs/troubleshooting.md).

## Documentation

[docs/index.md](docs/index.md): installation, customisation, architecture, compatibility, troubleshooting, design notes,
development, FAQ.

## Related repositories

- [m3e-gnome-extensions](https://github.com/maximeallanic/m3e-gnome-extensions): M3E Motion, M3E for Extensions and
  Status Bar (GNOME Shell 50).

## Language

The theme draws no text of its own, so it works in any language GNOME does; the extensions have no user interface
strings. Percentages in the status bar use `Intl.NumberFormat`. Tool output that the installer parses is read with
`LC_ALL=C`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/development.md](docs/development.md). Security reports:
[SECURITY.md](SECURITY.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## Credits

- [Material-Gnome](https://github.com/SakibShahariar/material-gnome-theme) by Sakib Shahriar Shimanto (GPL-3.0-or-later): the base GTK 3/4 theme.
- [Papirus icon theme](https://github.com/PapirusDevelopmentTeam/papirus-icon-theme) and papirus-folders.
- [matugen](https://github.com/InioX/matugen): template renderer.
- [material-color-utilities](https://github.com/material-foundation/material-color-utilities): palette maths.
- [Material Symbols](https://github.com/google/material-design-icons) (Apache-2.0).
- AOSP pointer drawables (Apache-2.0), used to build the Googlebook cursor.
- [Google Sans Flex](https://github.com/google/fonts/tree/main/ofl/googlesansflex) (SIL OFL 1.1).
- [Materia sound theme](https://github.com/nana-4/materia-sound-theme).
- Material 3 tokens and motion values from AndroidX and Material Components (Apache-2.0).

Third-party code is fetched at install time at a pinned commit and is never committed here. Licences and exact
usage: [NOTICE.md](NOTICE.md). Material Design, Android, Pixel and Google are trademarks of Google LLC; this project
is not affiliated with or endorsed by Google, GNOME or any project above.

## Licence

[MIT](LICENSE) for the code and original assets of this repository. Third-party components keep their own licences
([NOTICE.md](NOTICE.md)).
