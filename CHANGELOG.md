# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
