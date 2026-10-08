# Customisation

Anything you edit under `~/.config/m3e-gnome/` is overwritten by the next `./install.sh`, because that directory is
owned by the installer. Keep your changes small, and re-apply them after an update.

## Where the colours come from

`material-sync` chooses a source image, in this order:

1. **Hanabi live wallpaper (optional).** Only if the [Hanabi](https://github.com/jeffshee/gnome-ext-hanabi) extension
   is enabled and has a video: the image next to the video (same file name, or the closest name in the folder),
   otherwise one frame of the video taken with ffmpeg. Skipped silently when the extension, dconf or ffmpeg is absent.
   `MATERIAL_SYNC_HANABI=0` disables it (for example in a systemd drop-in). This project does not install Hanabi.
2. **The GNOME background.** `picture-uri-dark` in dark mode, `picture-uri` in light mode. GNOME dynamic wallpapers
   (`.xml`), `.svg` and `.jxl` files are converted to an image first.
3. **A fallback colour.** With no readable image, `material-sync` renders nothing and the installer seeds the palette
   from `fallback_color` in `palette.json`.

Change the wallpaper in GNOME Settings and the palette follows within a few seconds. The service watches the wallpaper,
the colour scheme, the Hanabi keys and the list of enabled extensions, waits 2 s after the last change, and runs
`material-sync`. A run whose inputs did not change is skipped; force one with:

```sh
~/.local/bin/material-sync --force
```

The log is `~/.cache/material-sync/material-sync.log`.

### Using a fixed colour

```sh
~/.local/bin/material-palette --color "#7B9F1C" --mode dark \
    --matugen-config ~/.config/m3e-gnome/matugen/config.toml
```

This renders the templates from that seed. It does not reload the Shell or GTK themes (only `material-sync` does that
by toggling the theme names), so log out and in, or run it and then change the wallpaper. The next wallpaper change
replaces your colour.

## Palette settings: `palette.json`

`~/.config/m3e-gnome/matugen/palette.json` is read by `material-palette` (not by matugen):

| Key | Meaning | Shipped value |
|---|---|---|
| `scheme` | Material scheme variant | `scheme-tonal-spot` |
| `spec` | Material colour specification | `2025` |
| `platform` | `phone` or `watch` as defined by material-color-utilities | `phone` |
| `contrast` | -1 to 1; 0 is standard | `0.0` |
| `fallback_color` | seed when there is no image | `#b7966a` |
| `custom_colors` | the six terminal ANSI colours, harmonised toward the seed | red, green, yellow, blue, magenta, cyan |

Accepted `scheme` values are the ones `tools/material-palette/lib.mjs` defines: `scheme-content`, `scheme-expressive`,
`scheme-fidelity`, `scheme-fruit-salad`, `scheme-monochrome`, `scheme-neutral`, `scheme-rainbow`, `scheme-tonal-spot`,
`scheme-vibrant`. Only `scheme-tonal-spot` with the 2025 spec at contrast 0 is what the project was designed and
checked with; the others render but are untested against the stylesheets. The contents of this file are part of the
change-detection key, so edit it and run `material-sync --force`.

The shipped contrast is standard (0), deliberately: a Pixel in high-contrast mode gives different roles (see
[design notes](design-notes.md)).

## Dark and light

The mode follows `org.gnome.desktop.interface color-scheme`:

```sh
gsettings set org.gnome.desktop.interface color-scheme prefer-dark   # dark
gsettings set org.gnome.desktop.interface color-scheme prefer-light  # light
```

`./install.sh --dark` (default) or `--light` sets it at install time, and `--keep-color-scheme` leaves it as it is.
Switching modes triggers a new sync (the service watches the colour scheme, and the source image differs per mode).
GTK 4 applications already running, Chrome included, follow the switch live: the GTK 4 `colors.css` holds both palettes
(dark inside `@media (prefers-color-scheme: dark)`, evaluated live by GTK 4.20 and later, which GNOME 50 ships). GTK 3
has no media queries: GTK 3 applications keep the mode they were started in until they are restarted. A GTK 4 older
than 4.20 does not understand the query and would always get the light palette. The theme is designed to be mostly
used in dark mode; see [troubleshooting](troubleshooting.md#light-mode) for light-mode quirks.

## Accent colour and folder colour

Each render sets two things from the primary colour: the GNOME accent (`org.gnome.desktop.interface accent-color`) to
the closest of the nine GNOME presets, and the Papirus folder colour (through `papirus-folders`) to the closest preset
there. They are approximations of the palette, not exact roles. To stop this, remove the `post_hook` lines of the
`gnome-accent` and `papirus-folders` templates in `~/.config/m3e-gnome/matugen/config.toml` (re-installing restores
them).

## Cursor

`black` (default) or `white`:

```sh
./install.sh --cursor white
```

This builds the cursor theme `Googlebook` or `Googlebook-White` into `~/.local/share/icons`, sets `cursor-theme` and
`cursor-size` (24) and points `~/.icons/default` at it. You can also switch with
`gsettings set org.gnome.desktop.interface cursor-theme Googlebook-White` once it is built.

## Fonts

The installer sets the interface font to `Google Sans Flex 10.5` and the title-bar font to `Google Sans Flex Bold 11`.
The title-bar font is a window-manager setting, so the CSS rule below does not govern it. Change them in GNOME Tweaks or
with `gsettings`; skip the step with `--skip font`.

## The no-bold rule

The theme never uses bold. It is enforced in four places:

- GTK 3: `no-bold-gtk3.css` sets `font-weight: normal` on everything.
- GTK 4 / libadwaita: the installer rewrites bold weights (`bold`, `bolder`, 600 to 900) in the installed
  Material-Gnome GTK 4 stylesheets, and `no-bold-gtk4.css` also pins the variable font's `wght` axis to 400, which beats
  a bold written by an application itself.
- Shell: the last stylesheet part (`99-no-bold.css`) with `!important`, since St has no user priority.
- The token checker (`dev/m3e-bench/verify_tokens.py`) rejects any bold in the sources.

To allow bold again, remove the `no-bold-*.css` imports from `~/.config/gtk-3.0/gtk.css` and
`~/.config/gtk-4.0/gtk*.css`; the Material-Gnome weights stay normalised until you reinstall it. This is unsupported.

## Design tokens

Every number in the M3E stylesheets either cites a Material 3 token in a comment (for example
`/* Switch.TrackWidth */`) or carries `M3E-visual: <reason>`. The token table is `dev/reference/m3e-tokens.json`
(from AndroidX) and `dev/m3e-bench/verify_tokens.py` checks the sources against it. Spring values for GTK are in
`theme/motion/gtk/` and are generated, not edited by hand. See [development](development.md).

## Ptyxis

The installer sets the default profile's palette to `material`, rendered by matugen into
`~/.local/share/org.gnome.Ptyxis/palettes/material.palette`, and leaves the profile's opacity alone. To go back:

```sh
gsettings set org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/<uuid>/ palette 'nord'
```

If you choose another Ptyxis palette, `theme/bin/ptyxis-active-tab` can give the active tab the terminal's colours; it
is a manual step described in `theme/overrides/README.md`.
