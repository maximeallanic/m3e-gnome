#!/usr/bin/env bash
# m3e-gnome installer: Material 3 Expressive theme for GNOME. Runs as your user (no root), changes only your home
# directory, is idempotent, and is fully reversible with ./uninstall.sh.
#
#   ./install.sh [options]
#
# Options:
#   --dry-run             print what would be done, change nothing
#   -y, --yes             do not ask for confirmation (dependency install, uninstall)
#   --install-deps        install missing system packages with sudo (asks first)
#   --dark | --light      colour scheme to set (default: --dark); --keep-color-scheme leaves it unchanged
#   --cursor black|white  Googlebook cursor variant (default: black)
#   --no-extensions       do not install the companion GNOME Shell extensions
#   --extensions-only     install only the companion extensions
#   --extensions-dir DIR  use a local m3e-gnome-extensions checkout instead of fetching it
#   --skip STEP           skip a step (repeatable): gtk-theme icons cursor sounds font palette extensions
#   --no-session-check    do not require a running GNOME session (for packaging and tests)
#   --gdm                 also theme the GDM login screen (opt-in, uses sudo for that step only; see docs/gdm.md)
#   --gdm-only            only the GDM step (needs a previous full install: it reuses the palette engine)
#   --gdm-image FILE      seed colour and blurred background of the login screen (default: your dark wallpaper)
#   --gdm-force           let the GDM helper run on a GNOME Shell major it was not verified with
#   --uninstall           remove everything this installer installed (same as ./uninstall.sh)
#   --version, -h, --help
#
# See README.md. Backups of everything replaced: ~/.local/share/m3e-gnome/backup/<timestamp>/ (restore.sh).
set -euo pipefail

REPO_ROOT="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
LIB="$REPO_ROOT/lib"
# shellcheck source=lib/common.sh
source "$LIB/common.sh"
for f in pins manifest backup fetch matugen deps settings steps_theme steps_config steps_settings gdm_prepare gdm; do
    # shellcheck source=/dev/null
    source "$LIB/$f.sh"
done
if [[ -n "${M3E_PINS_FILE:-}" ]]; then
    # shellcheck source=/dev/null
    source "$M3E_PINS_FILE"
fi   # tests and packagers: redefine the pins
EXT_HELPER_PY="$LIB/enabled_extensions.py"

ALL_STEPS=(gtk-theme icons cursor sounds font palette extensions)
declare -A SELECTED=()
ASSUME_YES=0
INSTALL_DEPS=0
COLOR_SCHEME=dark
CURSOR_STYLE=black
EXTENSIONS_DIR=''
SESSION_CHECK=1
USER_THEME_MISSING=0
TARGET_GNOME=50
ONLY_EXTENSIONS=0
WANT_GDM=0
GDM_ONLY=0
SKIPPED=()

step_enabled() { [[ -n "${SELECTED[$1]:-}" ]]; }
usage() { sed -n '2,/^# See README/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//; /^See README/d'; }

parse_args() {
    local s
    while (($#)); do
        case "$1" in
            --dry-run) DRY_RUN=1 ;;
            -y|--yes) ASSUME_YES=1 ;;
            --install-deps) INSTALL_DEPS=1 ;;
            --dark) COLOR_SCHEME=dark ;;
            --light) COLOR_SCHEME=light ;;
            --keep-color-scheme) COLOR_SCHEME=keep ;;
            --cursor)
                (($# >= 2)) || die "--cursor needs black or white"
                [[ "$2" == black || "$2" == white ]] || die "--cursor expects black or white"
                CURSOR_STYLE="$2"; shift ;;
            --no-extensions) SKIPPED+=(extensions) ;;
            --extensions-only) ONLY_EXTENSIONS=1 ;;
            --extensions-dir) (($# >= 2)) || die "--extensions-dir needs a directory"; EXTENSIONS_DIR="$2"; shift ;;
            --skip)
                (($# >= 2)) || die "--skip needs a step name"
                [[ " ${ALL_STEPS[*]} " == *" $2 "* ]] || die "unknown step '$2' (steps: ${ALL_STEPS[*]})"
                SKIPPED+=("$2"); shift ;;
            --gdm) WANT_GDM=1 ;;
            --gdm-only) WANT_GDM=1; GDM_ONLY=1 ;;
            --gdm-image) (($# >= 2)) || die "--gdm-image needs a file"; GDM_IMAGE="$2"; shift ;;
            --gdm-force) GDM_FORCE=1 ;;
            --no-session-check) SESSION_CHECK=0 ;;
            --uninstall) exec bash "$REPO_ROOT/uninstall.sh" "${@:2}" ;;
            --version) echo "m3e-gnome $M3E_VERSION"; exit 0 ;;
            -h|--help) usage; exit 0 ;;
            *) die "unknown option: $1 (see --help)" ;;
        esac
        shift
    done
    for s in "${ALL_STEPS[@]}"; do SELECTED[$s]=1; done
    if ((ONLY_EXTENSIONS)); then
        for s in "${ALL_STEPS[@]}"; do [[ "$s" == extensions ]] || unset "SELECTED[$s]"; done
    fi
    for s in "${SKIPPED[@]}"; do unset "SELECTED[$s]"; done
    if ((GDM_ONLY)); then SELECTED=(); fi
    ((${#SELECTED[@]} || GDM_ONLY)) || die "nothing to install: every step is skipped"
}

finish() {
    local status=$?
    if ((! DRY_RUN)) && [[ -n "$BACKUP_DIR" ]]; then write_restore_script; fi
    cleanup_tmp
    exit "$status"
}

summary() {
    msg_step "Done"
    if ((DRY_RUN)); then msg_info "dry run: nothing was changed"; return 0; fi
    if ((GDM_ONLY)); then
        msg_info "Check:     ./verify.sh --gdm   (the user-level checks fail until a full ./install.sh has run)"
        msg_info "Undo:      ./uninstall.sh --gdm"
        return 0
    fi
    msg_info "Log out and back in: the Shell, the extensions and every GTK application load the theme at login."
    step_enabled palette && msg_info "Chrome: Settings > Appearance > Theme: \"GTK\" (otherwise it ignores the title bars)."
    ((USER_THEME_MISSING)) && msg_info "Then install the User Themes extension ($(user_theme_hint)) and re-run ./install.sh."
    msg_info "Check:     ./verify.sh"
    msg_info "Undo:      ./uninstall.sh   (backups of what was replaced: ${BACKUP_DIR:-none})"
    ((WARNINGS == 0)) || msg_info "$WARNINGS warning(s) above."
}

main() {
    parse_args "$@"
    init_paths
    ((DRY_RUN)) && msg_info "dry run: nothing will be changed"
    if ((GDM_ONLY)); then
        trap finish EXIT
        ((SESSION_CHECK)) && session_check
        step_gdm
        summary
        return 0
    fi
    msg_step "Checking the system"
    if ! check_deps; then
        if ((INSTALL_DEPS)); then
            install_deps
            check_deps || die "dependencies still missing"
        elif ((DRY_RUN)); then
            msg_warn "dependencies are missing (a real run would stop here)"
        else
            die "install the missing tools (command above), or run ./install.sh --install-deps"
        fi
    fi
    ((SESSION_CHECK)) && session_check
    m_init
    trap finish EXIT
    backup_init
    step_enabled gtk-theme && step_gtk_theme
    step_enabled icons && step_icons
    step_enabled cursor && step_cursor
    step_enabled sounds && step_sounds
    step_enabled font && step_font
    step_enabled palette && step_palette_files
    step_settings
    if step_enabled palette; then
        step_palette_render
        step_ptyxis
        step_palette_service
    fi
    step_enabled extensions && step_extensions
    ((WANT_GDM)) && step_gdm
    summary
}

main "$@"
