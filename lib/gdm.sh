# shellcheck shell=bash
# GDM login screen, orchestration: the only step of the installer that uses root, through sudo, after printing the exact
# plan and asking. Opt-in (--gdm / --gdm-only); also reverted by uninstall. See docs/gdm.md.
# Requires common.sh, gdm_prepare.sh.

GDM_LIBEXEC=/usr/local/libexec/m3e-gnome/gdm
GDM_LINK=/usr/local/sbin/m3e-gdm
GDM_STATE=/var/lib/m3e-gnome/gdm
GDM_FILES=(m3e-gdm common.sh build.sh mech.sh hooks.sh dconf.sh assets.sh cmd.sh ingest.py cssgate.py pnggate.py)
GDM_FORCE=0
# Test seam (user-level only): a throw-away root and no sudo. Honoured only with M3E_GDM_TEST=1, never as root.
GDM_SUDO=(sudo)
GDM_OWN=(-o root -g root)
GDM_DEST_ROOT=''
GDM_RUN=()   # the helper starts with an empty environment through its shebang; the test seam needs its variables
if [[ "${M3E_GDM_TEST:-}" == 1 && "$(id -u)" != 0 && -n "${M3E_GDM_ROOT:-}" ]]; then
    GDM_SUDO=(); GDM_OWN=(); GDM_RUN=(bash); GDM_DEST_ROOT="${M3E_GDM_ROOT%/}"
fi

gdm_helper_cmd() { printf '%s' "$GDM_DEST_ROOT$GDM_LIBEXEC/m3e-gdm"; }

gdm_require_user() {
    [[ "$(id -u)" != 0 ]] || die "run the installer as your normal user, not as root: it asks for sudo only for the GDM step"
    ((${#GDM_SUDO[@]} == 0)) || have sudo || die "sudo is required for the GDM step"
}

# Every existing ancestor of the destination must be owned by root (uid $2) and not group/world-writable: whoever can
# write one can replace the helper directory later. $3 (tests only) is where the walk stops.
gdm_ancestors_ok() { # path want-uid [stop-dir]
    local d="$1" want="${2:-0}" stop="${3:-/}" own mode
    while [[ ! -d "$d" ]]; do d="$(dirname -- "$d")"; done
    while :; do
        own="$(stat -c '%u' -- "$d")"; mode="$(stat -c '%a' -- "$d")"
        if [[ "$own" != "$want" || $((8#$mode & 8#022)) != 0 ]]; then
            msg_warn "$d must be owned by root and not group/world-writable (is uid $own, mode $mode): refusing to install the root helper below it"
            return 1
        fi
        [[ "$d" == "$stop" || "$d" == / ]] && return 0
        d="$(dirname -- "$d")"
    done
}

# The helper files go into a root-owned directory, copied from this checkout by `install` (root only reads them).
gdm_install_helper() {
    local f dest="$GDM_DEST_ROOT$GDM_LIBEXEC" mode p created=() list
    # Remember which parent directories this step creates, so that uninstall removes exactly those.
    for p in /usr/local /usr/local/libexec /usr/local/libexec/m3e-gnome /usr/local/sbin; do
        [[ -d "$GDM_DEST_ROOT$p" ]] || created+=("$p")
    done
    if ((${#GDM_SUDO[@]})); then gdm_ancestors_ok "$dest" 0 || die "unsafe directory above $GDM_LIBEXEC"; fi
    run "${GDM_SUDO[@]}" install -d -m 0755 "${GDM_OWN[@]}" -- "$dest"
    for f in "${GDM_FILES[@]}"; do
        mode=0644; [[ "$f" == m3e-gdm ]] && mode=0755
        run "${GDM_SUDO[@]}" install -m "$mode" "${GDM_OWN[@]}" -- "$REPO_ROOT/gdm/$f" "$dest/$f"
    done
    if ((! DRY_RUN)); then
        make_tmp; list="$REPLY/created-dirs"
        { ((${#created[@]})) && printf '%s\n' "${created[@]}"; true; } >"$list"
        run "${GDM_SUDO[@]}" install -m 0644 "${GDM_OWN[@]}" -- "$list" "$dest/created-dirs"
    fi
    run "${GDM_SUDO[@]}" install -d -m 0755 "${GDM_OWN[@]}" -- "$(dirname -- "$GDM_DEST_ROOT$GDM_LINK")"
    run "${GDM_SUDO[@]}" ln -sfn -- "../libexec/m3e-gnome/gdm/m3e-gdm" "$GDM_DEST_ROOT$GDM_LINK"
}

gdm_describe() {
    msg_info "This step changes the SYSTEM, as root (sudo), and only these things:"
    msg_info "  - installs the helper into $GDM_LIBEXEC (root-owned) and the link $GDM_LINK"
    msg_info "  - replaces the GNOME Shell theme resource used by the login screen (mechanism chosen by the helper, see the plan)"
    msg_info "  - copies the Material-Symbols icons, the cursor and the font to /usr/local/share, the blurred wallpaper to /usr/local/share/m3e-gnome/gdm"
    msg_info "  - adds a dconf database for the gdm profile under /etc/dconf, and a package-manager hook that rebuilds the resource after updates"
    msg_info "  - records every path in $GDM_STATE/manifest; ./uninstall.sh --gdm (or sudo m3e-gdm restore) undoes it exactly"
}

step_gdm() {
    msg_step "GDM login screen (opt-in, needs sudo)"
    gdm_require_user
    gdm_describe
    local data theme
    theme="$(gs_get org.gnome.shell.extensions.user-theme name 2>/dev/null || true)"
    if [[ "$theme" != M3E-Shell ]]; then
        msg_warn "your Shell theme is '${theme:-unset}', not M3E-Shell. On systems where the login screen and the session share one stylesheet (Debian) the login sheet would also apply to your session: run ./install.sh first, or accept that"
    fi
    if ((DRY_RUN)) && [[ ! -x "$BIN_DIR/material-palette" ]]; then
        msg_info "[dry-run] would render the greeter stylesheet, blur the wallpaper, then show the plan and ask before using sudo"
        return 0
    fi
    make_tmp; data="$REPLY/data"
    gdm_prepare "$data"
    msg_info "plan (computed by the helper in dry-run mode, as your user, nothing is changed yet):"
    local plan=("${GDM_RUN[@]}" "$REPO_ROOT/gdm/m3e-gdm" apply --from "$data" --dry-run)
    ((GDM_FORCE)) && plan+=(--force)
    "${plan[@]}" || die "the helper refused the plan (see above)"
    if ((DRY_RUN)); then msg_info "dry run: no sudo command was run"; return 0; fi
    confirm "Apply this plan with sudo?" || die "aborted (use --yes to skip this question)"
    gdm_install_helper
    local apply=("${GDM_SUDO[@]}" "${GDM_RUN[@]}" "$(gdm_helper_cmd)" apply --from "$data")
    ((GDM_FORCE)) && apply+=(--force)
    "${apply[@]}" || die "the GDM step failed; nothing is half-applied that 'sudo m3e-gdm restore' cannot undo"
    msg_info "Login screen themed. It changes at the next boot or after 'sudo systemctl restart gdm' (that ends your session: save your work)."
    msg_info "Recovery from a TTY: sudo m3e-gdm restore   (or reinstall gnome-shell, see docs/gdm.md)"
}

gdm_installed() { [[ -f "$GDM_DEST_ROOT$GDM_STATE/manifest" ]]; }

# Uninstall side: revert through the installed helper, then remove the helper itself.
gdm_uninstall() {
    if ! gdm_installed && [[ ! -x "$(gdm_helper_cmd)" ]]; then msg_info "GDM theming: not installed"; return 0; fi
    gdm_require_user
    msg_step "Reverting the GDM login screen (sudo)"
    local cmd
    cmd="$(gdm_helper_cmd)"
    [[ -x "$cmd" ]] || die "$cmd is missing: reinstall the helper with ./install.sh --gdm-only, or reinstall gnome-shell to get the stock resource back (docs/gdm.md)"
    "${GDM_RUN[@]}" "$cmd" restore --dry-run || die "the helper could not plan the restore"
    if ((DRY_RUN)); then return 0; fi
    confirm "Revert the GDM theming with sudo?" || die "aborted (use --yes to skip this question)"
    "${GDM_SUDO[@]}" "${GDM_RUN[@]}" "$cmd" restore --remove-helper
}
