#!/usr/bin/env bash
# Check the git pins of lib/pins.sh: each revision must be a full 40-hex commit that can be fetched from its
# repository (the way the installer fetches it: `git fetch --depth 1 URL REV`; `git ls-remote` only lists refs, so it
# cannot confirm an arbitrary commit). Needs network. Exit status 0 when every pin is good.
#
#   scripts/check-pins.sh [--ext-only]     --ext-only: only the companion extensions pin (EXT_REV)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/pins.sh
source "$ROOT/lib/pins.sh"

names=(EXT MATGNOME PAPIRUS FOLDERS MATERIA)
case "${1:-}" in
    --ext-only) names=(EXT) ;;
    -h|--help) sed -n '2,7p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    '') ;;
    *) echo "usage: check-pins.sh [--ext-only]" >&2; exit 2 ;;
esac

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
git init -q -- "$tmp/repo"
status=0
for n in "${names[@]}"; do
    url_var="${n}_URL"; rev_var="${n}_REV"
    url="${!url_var}"; rev="${!rev_var}"
    if [[ ! "$rev" =~ ^[0-9a-f]{40}$ ]]; then echo "FAIL  $n: '$rev' is not a full 40-hex commit"; status=1; continue; fi
    if git -C "$tmp/repo" fetch -q --depth 1 -- "$url" "$rev" 2>/dev/null; then echo "ok    $n @ ${rev:0:12} ($url)"
    else echo "FAIL  $n: cannot fetch $rev from $url"; status=1; fi
done
exit "$status"
