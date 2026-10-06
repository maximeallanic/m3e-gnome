#!/usr/bin/env bash
# Builds material-palette: installs the pinned material-color-utilities (package-lock.json) and bundles palette.mjs
# into one self-contained file (the published package uses extension-less ESM imports that Node cannot resolve
# without a bundler). Output: $1, default ~/.local/lib/material-palette/palette.mjs.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HOME/.local/lib/material-palette/palette.mjs}"
cd "$HERE"
npm ci --no-audit --no-fund --loglevel=error
mkdir -p "$(dirname "$OUT")"
npx --no-install esbuild palette.mjs --bundle --platform=node --format=esm --log-level=warning --outfile="$OUT"
echo "material-palette: $OUT"
