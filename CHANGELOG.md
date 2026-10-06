# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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

- **GDM login-screen theming.** The private version ran a user-writable script as root; that design is not ported.
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
