# tools

Build-time tools of the theme. `papirus-symbolic.py [ICONS_DIR]` builds the `Papirus-Symbolic` theme (only Papirus' symbolic
directories, linked) so `Material-Symbols` can inherit from it without GTK indexing all of Papirus (about 1 s saved per app start).
`gtk4-two-modes.sh <gtk-4.0/colors-template.css>` rewrites Material-Gnome's GTK 4 matugen template so the rendered
`colors.css` holds the light palette by default and the dark one inside `@media (prefers-color-scheme: dark)` (the
installer runs it on `~/.themes/Material-Gnome`; idempotent).
`material-symbols/` builds the `Material-Symbols` icon theme and checks it against the common ink grid
(`check_ink_grid.py`).
Tests: `python3 -m unittest discover -s tests`. See each subdirectory for the others.
