# googlebook-cursors

Builds the Googlebook cursor theme (desktop Android's vector pointers, AOSP `frameworks/base`, Apache 2.0) as Xcursor files without
`xcursorgen`: the VectorDrawables are fetched from a pinned AOSP commit, converted to SVG, rendered with `rsvg-convert`
at 24-96 px and encoded by `xcursor.py`.

`python3 build.py [black|white] [--icons-dir DIR]` writes `DIR/Googlebook` (or `Googlebook-White`); default DIR
`$XDG_DATA_HOME/icons`. Needs `rsvg-convert`. Tests: `python3 -m unittest discover -s tests`.
