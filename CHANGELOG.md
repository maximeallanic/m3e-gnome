# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
- The companion extensions repository is fetched from its default branch until its first release is pinned.
