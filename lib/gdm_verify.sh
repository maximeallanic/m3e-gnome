# shellcheck shell=bash
# Read-only checks of the GDM login-screen theming, run as the user (everything it reads is world-readable). Used by
# verify.sh when /var/lib/m3e-gnome/gdm/manifest exists. Requires verify_checks.sh (v_ok/v_fail/v_warn), gdm.sh.

gdm_sha() { sha256sum -- "$1" | cut -d' ' -f1; }
gdm_has_marker() { gresource extract "$1" /org/gnome/shell/theme/gnome-shell-dark.css 2>/dev/null | grep -cF '/* m3e-gnome gdm */' | grep -qx 1; }
gdm_owner_ok() { # path : owned by root (by the invoking user in the test seam), not group/world-writable
    local want=0 own mode
    [[ -n "$GDM_DEST_ROOT" ]] && want="$(id -u)"
    own="$(stat -c '%u' -- "$1")"; mode="$(stat -c '%a' -- "$1")"
    [[ "$own" == "$want" ]] && (((8#$mode & 8#022) == 0))
}

check_gdm() {
    local st="$GDM_DEST_ROOT$GDM_STATE" r="$GDM_DEST_ROOT" mech live stock f bad=0 want
    local gres="$r/usr/share/gnome-shell/gnome-shell-theme.gresource"
    if [[ ! -f "$st/manifest" ]]; then v_fail "GDM: not installed (no $GDM_STATE/manifest); run ./install.sh --gdm"; return; fi
    mech="$(cat -- "$st/mech" 2>/dev/null || true)"
    case "$mech" in divert|alternatives|inplace) v_ok "GDM: mechanism $mech" ;; *) v_fail "GDM: unknown mechanism '$mech'"; return ;; esac

    # Helper: root-owned, identical to this checkout.
    local helper_dir="$r$GDM_LIBEXEC"
    if [[ -x "$helper_dir/m3e-gdm" && -L "$r$GDM_LINK" ]]; then
        for f in "${GDM_FILES[@]}"; do
            if [[ ! -f "$helper_dir/$f" ]]; then bad=1; v_fail "GDM helper file missing: $f"
            elif ! gdm_owner_ok "$helper_dir/$f"; then bad=1; v_fail "GDM helper file not root-owned or writable by others: $f"
            elif ! cmp -s -- "$REPO_ROOT/gdm/$f" "$helper_dir/$f"; then bad=1; v_fail "GDM helper differs from this checkout: $f (re-run ./install.sh --gdm-only)"; fi
        done
        ((bad)) || v_ok "GDM helper: root-owned and identical to the repository"
    else
        v_fail "GDM helper missing ($GDM_LINK): restoring needs reinstalling it (./install.sh --gdm-only)"
    fi

    # Staged data (what the helper rebuilds from).
    if [[ -f "$st/data.sha256" && -d "$st/data" ]] && [[ "$(python3 -I "$REPO_ROOT/gdm/ingest.py" hash "$st/data" 2>/dev/null)" == "$(cat -- "$st/data.sha256")" ]]; then
        v_ok "GDM staged data matches its recorded hash"
    else
        v_fail "GDM staged data is missing or does not match $GDM_STATE/data.sha256"
    fi

    # Resource state.
    case "$mech" in
        divert)
            live="$gres"; stock="$gres.distrib"
            if [[ "$(dpkg-divert ${GDM_DEST_ROOT:+--admindir "$r/var/lib/dpkg" --instdir "$r"} --listpackage /usr/share/gnome-shell/gnome-shell-theme.gresource 2>/dev/null)" == m3e-gnome ]]; then
                v_ok "GDM: stock resource diverted to .distrib by m3e-gnome"
            else v_fail "GDM: the diversion of gnome-shell-theme.gresource is missing"; fi
            if [[ -f "$stock" ]] && ! gdm_has_marker "$stock"; then v_ok "GDM: the diverted stock resource is stock"
            else v_fail "GDM: $stock is missing or not stock"; fi ;;
        alternatives)
            live="$r/usr/local/share/m3e-gnome/gdm/gdm-theme.gresource"; stock=''
            local n sel=''
            for n in gdm-theme.gresource gdm3-theme.gresource; do
                if sel="$(update-alternatives ${GDM_DEST_ROOT:+--altdir "$r/etc/alternatives" --admindir "$r/var/lib/dpkg/alternatives"} --query "$n" 2>/dev/null | sed -n 's/^Value: //p')" && [[ -n "$sel" ]]; then break; fi
            done
            if [[ "${sel#"$r"}" == /usr/local/share/m3e-gnome/gdm/gdm-theme.gresource ]]; then v_ok "GDM: our resource is the selected alternative"
            else v_fail "GDM: the gdm theme alternative does not select our resource (selected: ${sel:-none})"; fi ;;
        inplace)
            live="$gres"; stock="$st/stock/gnome-shell-theme.gresource"
            if [[ -f "$stock" ]]; then v_ok "GDM: stock resource copy kept"; else v_fail "GDM: stock copy missing"; fi ;;
    esac
    if [[ -f "$live" ]] && gdm_has_marker "$live"; then v_ok "GDM: the live resource carries the M3E sheet"
    else v_fail "GDM: the live resource does not carry the M3E sheet (a package update replaced it? run: sudo m3e-gdm refresh)"; fi
    want="$(cat -- "$st/built.sha256" 2>/dev/null || true)"
    if [[ -f "$live" && -n "$want" && "$(gdm_sha "$live")" == "$want" ]]; then v_ok "GDM: live resource is the one we built"
    else v_fail "GDM: live resource differs from the recorded build (run: sudo m3e-gdm refresh)"; fi
    if [[ -f "$st/disabled" ]]; then v_warn "GDM: disabled because GNOME Shell is not the verified major (stock sheet in service); sudo m3e-gdm refresh --force to override"; fi
    if [[ -n "$stock" && -f "$stock" && -f "$st/stock.sha256" ]]; then
        if [[ "$(gdm_sha "$stock")" == "$(cat -- "$st/stock.sha256")" ]]; then v_ok "GDM: built from the current stock resource"
        else v_fail "GDM: the stock resource changed since the build (run: sudo m3e-gdm refresh)"; fi
    fi

    # dconf, assets, hook.
    if grep -qx 'system-db:m3e-gdm' "$r/etc/dconf/profile/gdm" 2>/dev/null && [[ -s "$r/etc/dconf/db/m3e-gdm" && -f "$r/etc/dconf/db/m3e-gdm.d/00-m3e-gdm" ]]; then
        v_ok "GDM: dconf profile and database in place"
    else v_fail "GDM: dconf profile/database for the gdm user missing"; fi
    local t
    for t in "$r"/usr/local/share/icons/Material-Symbols/index.theme "$r"/usr/local/share/m3e-gnome/gdm; do
        [[ -e "$t" ]] || v_warn "GDM: missing asset ${t#"$r"} (the greeter falls back to defaults)"
    done
    case "$(M3E_OS_RELEASE="$r/etc/os-release" os_family)" in
        debian) v_if "GDM: apt refresh hook present" "GDM: apt hook missing" test -f "$r/etc/apt/apt.conf.d/99m3e-gdm" ;;
        arch) v_if "GDM: pacman refresh hook present" "GDM: pacman hook missing" test -f "$r/etc/pacman.d/hooks/m3e-gdm.hook" ;;
        fedora) if [[ -f "$r/etc/dnf/plugins/post-transaction-actions.d/m3e-gdm.action" || -f "$r/etc/dnf/libdnf5-plugins/actions.d/m3e-gdm.actions" ]]; then
            v_ok "GDM: dnf refresh hook present"; else v_warn "GDM: no dnf refresh hook (plugin not installed?): run sudo m3e-gdm refresh after gnome-shell updates"; fi ;;
        *) v_warn "GDM: no refresh hook on this distribution: run sudo m3e-gdm refresh after gnome-shell updates" ;;
    esac
}
