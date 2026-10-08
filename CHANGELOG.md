# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Companion extensions pinned to m3e-gnome-extensions `9f8f5f4`: search terms highlighted without bold, steady
  charging bolt, motion tracks redrawn on every frame.
- Shell top bar on a common ink grid: status icons at 16 px (their ink as tall as the clock's capitals), 6 px between
  them, battery 12.6 px high, and 2 px above the clock digits so they sit on the icons' centre line.
- Quick Settings sliders: the leading icon is moved onto the column of the tile icons (8 px margin), on the first
  child only, so the volume slider's trailing chevron no longer shortens its track by 8 px.
- GTK 4 header bar icon buttons match the window buttons: 10 px ink in a 30 px circle with 2 px vertical margins, also
  for both halves of a split button (Files view menu) and for the icon of icon + label buttons; the back button is a
  30 px circle.
- GTK 4 icon buttons in content: 16 px icon (the size of list icons, 24 px before) in a 32 px circle.
- Material-Symbols on a common ink grid (`tools/material-symbols/ink_grid.py`), set on the window buttons: ink as tall
  as the capitals of the neighbouring text, stroke 15 % of it. Thin outlines everywhere (filled before) except the
  battery and a few `!` symbols; the Material Symbols weight is computed (application icons 600, status icons 300 to
  700 per symbol). Sizes stay in CSS per context, never in the icon files. `MS_FILL` now defaults to 0 and
  `MS_INK_HEIGHT` is gone (the status ink share is tied to the top bar's `icon-size`).
- The chevrons (`go-next`, `go-previous`, `pan-start`, `pan-end`) follow the status grid (ink 0.72 of the frame, like
  Android's tile chevron) instead of their original frame, which left 4.5 px of ink in header bars.
- New `tools/material-symbols/check_ink_grid.py` renders the committed icons at the sizes read from the stylesheets and
  checks them against the grid.

### Fixed

- Running GTK 4 applications, Chrome included, now follow the light/dark switch without a restart: the installer
  rewrites Material-Gnome's GTK 4 colour template (`tools/gtk4-two-modes.sh`) so `colors.css` holds the light palette
  and the dark one under `@media (prefers-color-scheme: dark)` (GTK 4.20 and later). `verify.sh` checks it.
- GTK 4 icon buttons stretched by their row (Wi-Fi rows in Settings) were ovals: their container and halos are now
  round radial gradients, sized to the box (Material-Gnome's 1000 % background size made the circle ten times too big,
  clipped into a pill). A checked flat icon button gets a round `secondary` container.
- GTK 4 navigation sidebars: 16 dp on both sides of the row content (the label touched the right edge of the pill),
  and the extra inset of Files' place rows is removed (the icon was 32 px from the left edge).
- Calendar "day with events" dots are now rendered by matugen in palette colours (`on_surface`, dimmed to 38 % outside
  the month, `on_primary` on today) into `~/.themes/M3E-Shell/gnome-shell/assets/`; the stock white dot was invisible in
  light mode and not dimmed. The installer records the three files and `verify.sh` checks them. The GDM greeter sheet
  drops these declarations (its resource has no such files) and keeps the stock dot.
- The `m3e-extensions` stylesheet takes over two stock `!important` declarations the theme cannot beat: the focus ring
  of dialog fields (the filled text field shows its 2 dp primary indicator only) and the calendar month label colour
  (`on_surface_variant`; it was nearly invisible in light mode).
- Weak Wi-Fi was an isolated dot: partial Wi-Fi and cellular levels now show the inactive arcs and bars at 30 %, as one
  group, like Android and Adwaita.
- The 44 `org.gnome.Settings-<panel>-symbolic` icons (Settings sidebar, Shell search) are mapped; they fell back to
  filled Papirus icons among the outlined ones.
- The Actions directories of Papirus-Dark are no longer declared in `Material-Symbols` (light-grey glyphs drawn for a
  dark background were washed out in light mode, e.g. a Reminders notification icon); those names resolve to their
  symbolic variant. `build.py` also removes Papirus links a previous build left behind (`18x18`).

## [0.1.0] - 2026-10-06

First public release (pre-release: the installer was run for real on the author's Debian machine with GNOME Shell
50.5, and in fake roots and nested headless shells; nothing else has been tried).

### Added

- **Release packaging**: the `m3e-gnome` Debian package (`scripts/build-deb.sh`): the read-only runtime tree under
  `/usr/share/m3e-gnome` with a prebuilt palette bundle (no npm at install time), the commands `m3e-gnome-install`,
  `m3e-gnome-uninstall` and `m3e-gnome-verify` (they refuse to run as root), man pages, bash completion. Installing the
  package changes no home directory and still needs network access when you run `m3e-gnome-install`. A
  tag-triggered release workflow (tests, `.deb`, source tarball, `SHA256SUMS`, provenance attestation, notes from this
  file, pin check), `scripts/release.sh`, `scripts/check-pins.sh`.
- The extensions step enables the system-wide extensions (`/usr/share/gnome-shell/extensions`, from the
  `gnome-shell-extension-m3e` package) instead of cloning the extensions repository; `--extensions-dir` still wins.
  `verify.sh` accepts them.

- **Opt-in GDM login-screen theming** (`./install.sh --gdm`, `--gdm-only`, `--gdm-image`, `--gdm-force`;
  `./uninstall.sh --gdm`; a GDM section in `./verify.sh`). A rebuild of the private script with a privilege boundary:
  a root-owned helper (`gdm/`) that treats user-prepared data as untrusted (no links, size/format limits, CSS `url()`
  allow-list, no `@import`), compiles and verifies the gresource in a root-owned directory and swaps it atomically.
  `dpkg-divert` on Debian, `update-alternatives` on Ubuntu, in place with a stock copy elsewhere; apt, pacman and DNF
  refresh hooks; greeter icons, cursor, font and dark scheme through a dconf database. Everything recorded in a root
  manifest and undone exactly. Debian verified in a fake root and a nested Shell; other distributions untested
  (see [docs/gdm.md](docs/gdm.md)). Hardened after an independent review: CSS checked on a token stream (comment
  markers in strings no longer bypass the `url()`/`@import` allow-list), bash `$EUID` and a purged environment as root,
  every ancestor directory checked, no `fc-cache`/`gtk-update-icon-cache` as root, PNG chunk validation and tighter caps,
  asset theme-name allow-list, a lock, a two-phase identity record, idempotent re-runs, and corrected recovery advice
  (a package reinstall does not undo the divert).

- First public release, extracted from a private desktop setup: Material 3 Expressive theme for GNOME 50 (GTK 3/4,
  libadwaita, Chrome, GNOME Shell), Material-Symbols icons, Googlebook cursor, Materia sounds, Google Sans Flex,
  and a palette computed as on a Pixel (2025 colour spec) from the wallpaper and rendered by matugen.
- `install.sh`: one command, no root, idempotent. `--dry-run`, `--yes`, `--install-deps`, `--dark`/`--light`,
  `--cursor`, `--skip STEP`, `--no-extensions`, `--extensions-only`, `--extensions-dir`. Per-distribution commands for
  missing tools (Debian/Ubuntu, Fedora, Arch, openSUSE). Every source pinned (commit or sha256); matugen 4.2.0
  installed from its checksum-verified release.
- `uninstall.sh`: removes exactly the paths listed in `~/.local/share/m3e-gnome/manifest` and restores the files and
  GNOME settings that were replaced (backup in `~/.local/share/m3e-gnome/backup/<timestamp>/`, with `restore.sh`).
- `verify.sh`: checks installed files, rendered outputs, GNOME settings, extensions and the service.
- Installer tests (round trip in a temporary home with fake GNOME tools) and CI.
- `dev/screenshots`: reproducible README screenshots (nested headless Shell with a fake home, system bus, audio and
  generated CC0 wallpapers), and the images in `screenshots/`.

### Not included

- Personal integrations of the original setup (live wallpaper, Home Assistant, the Orchis/theme-sync service).

### Fixed

- The installer no longer writes inside its own directory: `tools/material-palette/build.sh` builds in a temporary copy
  (it left `node_modules` next to the sources), Python bytecode caches are disabled, and `rsync` no longer copies the
  permissions of a read-only source tree into the user's home (which made the installed copy impossible to update or
  remove).
- GNOME Settings > Appearance: the accent colour swatches were invisible (the generic button rules at user priority
  overrode the application's `.accent-button`); `m3e-gtk4-buttons.css` now keeps their colour, size and selection ring.
- Light mode: the top bar over the overview (clock, status icons) used `on_surface` on the primary-coloured overview
  and was unreadable; `43-overview-light.css` now uses `on_primary` there.

### Known limitations

- Validated on GNOME Shell 50.5 only; other major versions get a warning.
- Only the default XDG layout is supported (`~/.config`, `~/.cache`, `~/.local/share`): the matugen config uses those
  paths literally.
- matugen release binaries exist for x86_64 only; other architectures must `cargo install matugen --version 4.2.0
  --locked` first.

[Unreleased]: https://github.com/maximeallanic/m3e-gnome/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maximeallanic/m3e-gnome/releases/tag/v0.1.0
