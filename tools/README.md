# tools

Build-time tools of the theme. `papirus-symbolic.py [ICONS_DIR]` builds the `Papirus-Symbolic` theme (only Papirus' symbolic
directories, linked) so `Material-Symbols` can inherit from it without GTK indexing all of Papirus (about 1 s saved per app start).
Tests: `python3 -m unittest discover -s tests`. See each subdirectory for the others.
