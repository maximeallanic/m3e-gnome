# bin

Scripts installed into `~/.local/bin` (all honour `XDG_CONFIG_HOME` / `XDG_CACHE_HOME`; nothing is hardcoded to a user).

- `material-palette`: computes a Material 3 palette (2025 colour spec, like a Pixel) with `tools/material-palette`'s bundle, then
  has matugen render every template of a matugen config. `material-palette (--image FILE | --color HEX) --mode light|dark
  [--json OUT] [--matugen-config TOML]`. Settings: `$XDG_CONFIG_HOME/m3e-gnome/matugen/palette.json` (or `$MATERIAL_PALETTE_CONFIG`);
  bundle: `~/.local/lib/material-palette/palette.mjs` (or `$MATERIAL_PALETTE_BUNDLE`).
- `material-sync [--force]`: picks the source image (see below), runs `material-palette`, then reloads the Shell and GTK themes. Skips when nothing changed. One run at
  a time (`flock`). Log: `$XDG_CACHE_HOME/material-sync/material-sync.log`.
- `material-sync-watch`: `dconf watch /` on the wallpaper, colour-scheme, Hanabi and enabled-extensions keys; runs
  `material-sync` 2 s after the last change. Exits non-zero if dconf dies so systemd restarts it.
- `ptyxis-active-tab [--output FILE] [--palette ID]`: optional, manual: writes `~/.config/m3e-gnome/ptyxis-active-tab.css`, the
  stylesheet that gives Ptyxis' active tab the terminal colours (setup in `../overrides/README.md`).

The two matugen files, `config.toml` (the templates and their targets) and `palette.json` (the palette settings), live in `~/.config/m3e-gnome/matugen/`; `config.toml` is always passed to matugen with `--config`, so a user's own
`~/.config/matugen/` is never read or replaced.

## Wallpaper sources (`material-sync`), in order

1. Optional [Hanabi](https://github.com/jeffshee/gnome-ext-hanabi) live wallpaper, only if its extension is enabled and has a video:
   the image next to the video (same name, else the closest name in the folder), else one frame of the video (ffmpeg). Skipped
   when the extension, dconf or ffmpeg is absent; `MATERIAL_SYNC_HANABI=0` disables it (e.g. in a systemd drop-in).
2. The GNOME background: `picture-uri-dark` in dark mode, `picture-uri` in light mode (`.xml` dynamic wallpapers, `.svg`, `.jxl` are converted).
3. Fallback colour: with no readable image `material-sync` renders nothing and the installer seeds the palette from the
   `fallback_color` of `palette.json`.

All parsing of `gsettings`/`dconf` output is done with `LC_ALL=C` and is locale independent.
Tests: `python3 -m unittest discover -s tests` (no graphical session needed).
