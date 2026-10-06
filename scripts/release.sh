#!/usr/bin/env bash
# Check that the repository is ready to release VERSION, then print (never run) the tag commands.
#
#   scripts/release.sh [--ci] VERSION    VERSION like 0.1.0 or 0.2.0-rc1, without the leading v
#
# Checks: version format, M3E_VERSION in lib/common.sh equals VERSION, CHANGELOG.md has a section for it, EXT_REV in
# lib/pins.sh is a full 40-hex commit, clean working tree, the tag does not exist yet. It cannot check the network
# pins: run scripts/check-pins.sh for that (the release workflow does).
# --ci (release workflow): skip the working-tree and tag checks, print nothing to run.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
die() { echo "error: $*" >&2; exit 1; }

ci=0
if [[ "${1:-}" == --ci ]]; then ci=1; shift; fi
case "${1:-}" in -h|--help) sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;; esac
version="${1:-}"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || die "usage: release.sh [--ci] VERSION (like 0.1.0 or 0.2.0-rc1)"

found="$(sed -n 's/^M3E_VERSION=//p' "$ROOT/lib/common.sh")"
[[ "$found" == "$version" ]] || die "M3E_VERSION in lib/common.sh is '$found', expected $version"
"$ROOT/scripts/release-notes.sh" "$version" >/dev/null || die "CHANGELOG.md has no section [$version]"
ext_rev="$(sed -n 's/^EXT_REV=\([0-9a-f]*\).*/\1/p' "$ROOT/lib/pins.sh")"
[[ "$ext_rev" =~ ^[0-9a-f]{40}$ ]] || die "EXT_REV in lib/pins.sh is not a full 40-hex commit"
if [[ $ci -eq 0 ]]; then
    [[ -z "$(git -C "$ROOT" status --porcelain)" ]] || die "the working tree is not clean"
    if git -C "$ROOT" rev-parse -q --verify "refs/tags/v$version" >/dev/null; then die "tag v$version already exists"; fi
fi

[[ $ci -eq 0 ]] || { echo "version and pin format consistent: $version"; exit 0; }
case "$version" in
    0.*|*-*) kind="a pre-release" ;;
    *) kind="a stable release" ;;
esac
echo "Ready: v$version will be published as $kind (EXT_REV ${ext_rev:0:12})."
echo "Before tagging: scripts/check-pins.sh (network), and re-check that EXT_REV is the extensions release you want."
echo "Not done by this script (run them yourself, on main):"
echo "  git tag -s v$version -m 'v$version'     # or: git tag -a v$version -m 'v$version'"
echo "  git push origin v$version               # the Release workflow does the rest"
