#!/usr/bin/env bash
# Remove everything ./install.sh installed, and restore the files and settings it replaced.
#
#   ./uninstall.sh [--dry-run] [-y|--yes] [--gdm]
#
# Only paths recorded in ~/.local/share/m3e-gnome/manifest are removed, never by pattern. Files that existed before
# the install are put back from ~/.local/share/m3e-gnome/backup/<timestamp>/ and dconf keys get their old value.
# If the GDM login screen was themed (install.sh --gdm), it is reverted too, through sudo, after the plan is shown
# and confirmed. --gdm reverts only that part.
set -euo pipefail

REPO_ROOT="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/lib/common.sh"
for f in manifest backup uninstall gdm; do
    # shellcheck source=/dev/null
    source "$REPO_ROOT/lib/$f.sh"
done
EXT_HELPER_PY="$REPO_ROOT/lib/enabled_extensions.py"
ASSUME_YES=0
GDM_ONLY=0

while (($#)); do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        -y|--yes) ASSUME_YES=1 ;;
        --gdm) GDM_ONLY=1 ;;
        -h|--help) sed -n '2,/^set -e/p' "${BASH_SOURCE[0]}" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
    shift
done
init_paths
trap cleanup_tmp EXIT
if ((! GDM_ONLY)); then do_uninstall; fi
gdm_uninstall
