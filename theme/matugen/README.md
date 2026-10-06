# matugen

Both files are installed to `~/.config/m3e-gnome/matugen/` (not `~/.config/matugen/`, which stays the user's own) and given
to matugen with `--config`. `post_hook` commands run in a shell: paths in them use a quoted `"$HOME/..."`, so a HOME with
spaces or non-ASCII characters works.

- `config.toml`: matugen config; every template that gets rendered with the palette (GTK colours, Shell, extensions,
  Papirus folder colour, GNOME accent, Ptyxis, Chrome).
- `palette.json`: settings read by `material-palette` (not by matugen): scheme, colour spec (2025), platform, contrast,
  fallback seed colour and the custom ANSI colours for the terminal. Changing it makes `material-sync` regenerate.

matugen only renders templates here: `material-palette` computes the colours (matugen 4.2 knows the 2021 spec only) and
feeds them through `matugen json`.
