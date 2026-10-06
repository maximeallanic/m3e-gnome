# material-symbols

Builds the `Material-Symbols` icon theme from [Material Symbols](https://github.com/google/material-design-icons)
(pinned commit; downloaded into `$XDG_CACHE_HOME/m3e-gnome/material-symbols`).

- `map.py`: top-bar status icons, GNOME name -> symbol (`!` = filled). Partial Wi-Fi / cellular levels are drawn over the full glyph
  at 30 % opacity (`UNDERLAY`), like Android's inactive arcs and bars.
- `map_apps.py`: symbolic application icons (`!` filled, `^` flipped, `%` rotated).
- `symbols.py`: pure helpers (naming, SVG path extraction, framing maths).
- `build.py [--icons-dir DIR]`: writes `DIR/Material-Symbols` (default `$XDG_DATA_HOME/icons`), links the coloured folders of
  `Papirus-Dark` (must be installed in DIR) and runs `../papirus-symbolic.py`. Status SVGs carry `data-ink-width`, read by the status-bar extension.
  Needs `rsvg-convert` and `ffmpeg`. Env: `MS_STYLE`, `MS_FILL`, `MS_INK_HEIGHT`, `APP_INSET`.
- `bbox.json`, `bbox-outlined.json`: measured ink boxes (cache, committed).
- Tests: `python3 -m unittest discover -s tests`.
