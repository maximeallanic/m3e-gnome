# material-palette

Computes Material 3 colour roles the way a Pixel (Android 16+) does: the official
[`@material/material-color-utilities`](https://github.com/material-foundation/material-color-utilities) (pinned, 2025 spec,
phone platform), seed extracted from an image like Android's `WallpaperColors`. Output is JSON in the shape `matugen json` renders templates from.

- `palette.mjs`: CLI. `node palette.mjs --config palette.json (--image FILE | --color HEX) --mode light|dark [--output FILE]`. Needs `ffmpeg`/`ffprobe` for images.
- `lib.mjs`: pure logic (argument parsing, scheme and role computation), unit-tested.
- `build.sh [OUT]`: `npm ci` (in a temporary copy: this directory is never written) then bundles `palette.mjs` into one file (default `~/.local/lib/material-palette/palette.mjs`); the published
  library uses extension-less ESM imports Node cannot resolve without a bundler.
- Tests: `npm ci && npm test` (bundles the tests with esbuild, then `node --test`). They check that seed `#7B9F1C` gives the reference
  Pixel colours (`primary #1c2800`, `on_primary #cee29d`, `surface_container #eeefe1` at contrast 1.0).
