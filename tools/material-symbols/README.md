# material-symbols

Builds the `Material-Symbols` icon theme from [Material Symbols](https://github.com/google/material-design-icons)
(pinned commit; downloaded into `$XDG_CACHE_HOME/m3e-gnome/material-symbols`).

- `map.py`: top-bar status icons, GNOME name -> symbol (outlined; `!` = filled, only the battery). Partial Wi-Fi /
  cellular levels are drawn over the full glyph at 30 % opacity (`UNDERLAY`), like Android's inactive arcs and bars.
- `map_apps.py`: symbolic application icons (`!` filled, `^` flipped, `%` rotated), including every
  `org.gnome.Settings-<panel>-symbolic` panel icon.
- `ink_grid.py`: the common ink grid (ink height = cap height of the neighbouring text, stroke = 15 % of it, status
  symbols at 72 % of their frame) and the weight choice; also reads the grid sizes back from the stylesheets.
- `symbols.py`: pure helpers (naming, SVG path extraction, framing maths).
- `build.py [--icons-dir DIR]`: writes `DIR/Material-Symbols` (default `$XDG_DATA_HOME/icons`), links the coloured
  folders of `Papirus-Dark` (must be installed in DIR; its Actions directories are left out) and runs
  `../papirus-symbolic.py`. Status SVGs carry `data-ink-width`, read by the status-bar extension. Needs `rsvg-convert`
  and `ffmpeg`. Env: `MS_STYLE`, `MS_FILL`, `APP_INSET`.
- `check_ink_grid.py [--icons DIR]`: renders the committed icons at the sizes set in
  `theme/shell/m3e-shell/*.css` and `theme/overrides/m3e-gtk4*.css` and checks them against the grid. A `uv` script
  (fontTools reads the cap height of Google Sans Flex); needs `rsvg-convert`, `ffmpeg` and the font.
- `bbox.json`, `bbox-outlined.json`: measured ink boxes (cache, committed; `build.py` keeps only the boxes it used).
- Tests: `python3 -m unittest discover -s tests`.
