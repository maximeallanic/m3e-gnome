# Troubleshooting

Start with `./verify.sh`: it checks installed files, rendered outputs, GNOME settings, extensions and the service, and
prints `OK`, `WARN` or `FAIL` per item. A `WARN` is a state that fixes itself (usually: log out and in).

## Nothing changed after install

Log out and back in. The Shell, the extensions, the icon and cursor themes and GTK applications load the theme at
login. On Wayland the Shell cannot be restarted in place.

## The Shell theme does not load

The Shell theme needs the **User Themes** extension. The installer warns when its schema is missing. Install it
(`gnome-shell-extensions` on Debian, Ubuntu and Arch; `gnome-shell-extension-user-theme` on Fedora and openSUSE), run
`./install.sh` again, and log out and in.

## The extensions are inactive

- A newly copied extension is not known to the running Shell: it becomes active at the next login. `./verify.sh`
  reports it as a warning until then.
- Check the state: `gnome-extensions list --enabled` and `gnome-extensions info <uuid>`.
- Look for errors: `journalctl --user -b -o cat /usr/bin/gnome-shell | grep -E "m3e|status-bar"`. Messages are
  prefixed with the extension name.
- The extensions target GNOME Shell 50 only (`"shell-version": ["50"]`). On another version the Shell will not load
  them.
- Another extension that replaces the same Shell methods (window animations, overview) conflicts: enable one at a time.
- The extensions follow GNOME's *enable-animations* setting; with animations off nothing moves.
- If Blur my Shell is enabled the installer warns: this theme uses tinted surfaces instead of blur and the two can
  conflict.

## Colours do not follow the wallpaper

```sh
systemctl --user status material-sync.service
~/.local/bin/material-sync --force
tail ~/.cache/material-sync/material-sync.log
```

- No wallpaper image found (for example a missing file): `material-sync` logs "no source image found" and renders
  nothing. The installer then uses the `fallback_color` of `palette.json` for the first palette.
- The source differs per mode: dark mode reads `picture-uri-dark`, light mode `picture-uri`.
- `material-sync` needs `matugen` (installed in `~/.local/bin` or on the service's `PATH`), Node.js through the
  bundle `~/.local/lib/material-palette/palette.mjs`, and `ffmpeg` for images and videos.
- A run whose inputs did not change is skipped on purpose; use `--force`.

## Applications keep the old colours

GTK 4 applications and Chrome read the stylesheets when they start. Restart them. Nautilus keeps running as a service:
`nautilus -q`. Ptyxis keeps its palette in an already-open window until the palette setting changes; open a new window.

## Chrome

- Set *Settings > Appearance > Theme* to **GTK**. Without it Chrome ignores the title-bar styling.
- Chrome reads the CSS only at startup.
- In light mode Chrome's toolbar and active tab stay dark by design of the template (`chrome-dark-gtk4.template`).
- Web page backgrounds, the New Tab page and selection inside pages do not come from GTK.

## Light mode

The theme was designed for dark mode first and light mode is supported but less exercised. Known behaviours:

- Chrome toolbar and active tab dark (above).
- The lock screen and login screen are always dark (the blurred background is darkened by the Shell).
- Some Shell surfaces are close in tone in light mode (for example the "Run a command" field differs from its dialog
  by only a few levels per channel), so they read mostly by their indicator.

## The Shell stylesheet seems stale

The Shell caches its theme: it reloads only when the `user-theme` name changes, which `material-sync` does. If you edited
files by hand, run `~/.local/bin/material-sync --force`, or log out and in. Stylesheets of extensions are reloaded by
the extensions when `m3e-extensions.css` changes.

St silently ignores declarations it does not understand (unknown property or unit, `calc()`, percentage lengths,
per-side border shorthand). If you modify Shell CSS, check it with `dev/m3e-bench-shell/st_sheet.py` (see
[development](development.md)).

## Title bars of X11 and libdecor windows

The mutter X11 frames read their CSS only at start and mutter does not restart them; log out and in to see changes.
Their shadows and bottom corners come from mutter, libdecor or Qt and are not controlled by this theme. At a fractional
scale, X11 frames can look smaller (Xwayland upscaling). Untested beyond the author's setup.

## Slow application start

The icon theme intentionally inherits only `Papirus-Symbolic`, `Adwaita` and `hicolor`. If you change `Inherits` in
`~/.local/share/icons/Material-Symbols/index.theme` to a long chain, GTK applications start slower. Also install
`gtk-update-icon-cache` so the installer can build the icon cache.

## Uninstall and restore

```sh
./uninstall.sh --dry-run     # list what would happen
./uninstall.sh               # asks first; add -y to skip the question
```

- It disables the palette service, removes the extension UUIDs it added from `enabled-extensions`, deletes exactly the
  paths in `~/.local/share/m3e-gnome/manifest` (refusing anything outside `$HOME`, never expanding a pattern), then runs
  `restore.sh` from the backup: pre-existing files are moved back and every dconf key gets its old value.
- If something cannot be restored, the backup is kept and the messages say what. You can run the script by hand:
  `bash ~/.local/share/m3e-gnome/backup/<timestamp>/restore.sh`.
- When it succeeds it removes `~/.local/share/m3e-gnome/`. Log out and in afterwards.
- It does not uninstall system packages you installed with `--install-deps`, and it does not remove the User Themes
  extension if you installed that yourself.

## Reporting a bug

Include `./install.sh --version`, your distribution, the GNOME Shell version (`gnome-shell --version`), the output of
`./verify.sh` and the end of `~/.cache/material-sync/material-sync.log`. Use the bug report template.
