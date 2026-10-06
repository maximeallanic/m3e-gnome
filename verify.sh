#!/usr/bin/env bash
# Check an installation made by ./install.sh. Read-only. Exit status 0 when everything checks out.
#
#   ./verify.sh [--skip STEP]... [--no-extensions|--extensions-only] [--cursor black|white] [--no-service] [--strict]
#
#   --skip STEP / --no-extensions / --extensions-only / --cursor   same meaning as for install.sh (verify what you installed)
#   --no-service   do not require material-sync.service to be active
#   --gdm          require the GDM login-screen theming (checked anyway whenever it is installed)
#   --strict       treat warnings (e.g. an extension the running Shell has not loaded yet) as failures
set -uo pipefail

REPO_ROOT="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
LIB="$REPO_ROOT/lib"
# shellcheck source=lib/common.sh
source "$LIB/common.sh"
for f in pins matugen deps settings verify_checks gdm gdm_verify; do
    # shellcheck source=/dev/null
    source "$LIB/$f.sh"
done
if [[ -n "${M3E_PINS_FILE:-}" ]]; then
    # shellcheck source=/dev/null
    source "$M3E_PINS_FILE"
fi
USER_THEME_UUID=user-theme@gnome-shell-extensions.gcampax.github.com

ALL_STEPS=(gtk-theme icons cursor sounds font palette extensions)
declare -A SELECTED=()
CURSOR_STYLE=black
STRICT=0
ONLY_EXTENSIONS=0
CHECK_SERVICE=1
REQUIRE_GDM=0
step_enabled() { [[ -n "${SELECTED[$1]:-}" ]]; }

SKIPPED=()
while (($#)); do
    case "$1" in
        --skip) (($# >= 2)) || die "--skip needs a step name"; SKIPPED+=("$2"); shift ;;
        --no-extensions) SKIPPED+=(extensions) ;;
        --extensions-only) ONLY_EXTENSIONS=1 ;;
        --cursor) (($# >= 2)) || die "--cursor needs black or white"; CURSOR_STYLE="$2"; shift ;;
        --no-service) CHECK_SERVICE=0 ;;
        --gdm) REQUIRE_GDM=1 ;;
        --strict) STRICT=1 ;;
        -h|--help) sed -n '2,/^set -u/p' "${BASH_SOURCE[0]}" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
    shift
done
for s in "${ALL_STEPS[@]}"; do SELECTED[$s]=1; done
if ((ONLY_EXTENSIONS)); then
    for s in "${ALL_STEPS[@]}"; do [[ "$s" == extensions ]] || unset "SELECTED[$s]"; done
fi
for s in "${SKIPPED[@]}"; do unset "SELECTED[$s]"; done
init_paths

check_manifest
check_settings
check_files
if step_enabled palette; then
    check_palette_files
    check_rendered
    ((CHECK_SERVICE)) && check_service
fi
step_enabled extensions && check_extensions
if gdm_installed || ((REQUIRE_GDM)); then check_gdm; fi

echo
printf '%d ok, %d failed, %d warning(s)\n' "$V_OK" "$V_FAIL" "$V_WARN"
((V_FAIL == 0 && (!STRICT || V_WARN == 0)))
