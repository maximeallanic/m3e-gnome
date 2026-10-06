# shellcheck shell=bash
# GNOME settings and Shell extensions. Requires settings.sh, backup.sh, manifest.sh, fetch.sh.

USER_THEME_UUID=user-theme@gnome-shell-extensions.gcampax.github.com
EXT_HELPER_PY=''   # set by install.sh: lib/enabled_extensions.py

# Add UUIDs to enabled-extensions and remember which ones we added (uninstall removes exactly those).
enable_extensions() {
    local added list
    if ((DRY_RUN)); then msg_info "[dry-run] enable extensions: $*"; return 0; fi
    added="$(python3 "$EXT_HELPER_PY" add "$@")"
    [[ -n "$added" ]] || return 0
    added="${added//$'\n'/ }"
    list="$(state_get added_extensions) $added"
    state_set added_extensions "$(xargs <<<"$list")"
    msg_info "enabled: $added"
}

step_settings() {
    msg_step "GNOME settings"
    local I=org.gnome.desktop.interface cursor=Googlebook
    [[ "$CURSOR_STYLE" == white ]] && cursor=Googlebook-White
    backup_dynamic_keys
    if step_enabled gtk-theme; then
        gs_set $I gtk-theme "'Material-Gnome'"
        gs_set org.gnome.desktop.wm.preferences button-layout "'appmenu:minimize,maximize,close'"
    fi
    step_enabled icons && gs_set $I icon-theme "'Material-Symbols'"
    if step_enabled cursor; then
        gs_set $I cursor-theme "'$cursor'"
        gs_set $I cursor-size 24
    fi
    if step_enabled palette; then
        case "$COLOR_SCHEME" in
            dark) gs_set $I color-scheme "'prefer-dark'" ;;
            light) gs_set $I color-scheme "'prefer-light'" ;;
        esac
    fi
    if step_enabled font; then
        gs_set $I font-name "'Google Sans Flex 10.5'"
        gs_set org.gnome.desktop.wm.preferences titlebar-font "'Google Sans Flex Bold 11'"
    fi
    if step_enabled sounds; then
        gs_set org.gnome.desktop.sound theme-name "'Materia'"
        gs_set org.gnome.desktop.sound event-sounds true
    fi
    if step_enabled palette; then
        if ((DRY_RUN)) || gs_schema_exists org.gnome.shell.extensions.user-theme; then
            gs_set org.gnome.shell.extensions.user-theme name "'M3E-Shell'"
            enable_extensions "$USER_THEME_UUID"
        else
            USER_THEME_MISSING=1
            msg_warn "the GNOME 'User Themes' extension is not installed: the Shell theme cannot load. Install it ($(user_theme_hint)), then run ./install.sh again"
        fi
        # The dock gets its tinted surface from the theme, not from Dash to Dock's own theming.
        gs_set_if_schema org.gnome.shell.extensions.dash-to-dock apply-custom-theme false
    fi
}

# After the first palette: Ptyxis uses the rendered "material" palette (its opacity setting is left alone).
step_ptyxis() {
    gs_schema_exists org.gnome.Ptyxis || { msg_info "Ptyxis not installed: terminal palette left alone"; return 0; }
    local uuid
    uuid="$(gs_get org.gnome.Ptyxis default-profile-uuid)"
    [[ -n "$uuid" ]] || { msg_info "Ptyxis has no default profile yet: terminal palette left alone"; return 0; }
    gs_set "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/$uuid/" palette "'material'"
}

step_extensions() {
    msg_step "Shell extensions (m3e-motion, m3e-extensions, status-bar)"
    local repo stage uuid d uuids=()
    if use_system_extensions; then
        # Installed by the gnome-shell-extension-m3e package (or by hand): nothing to fetch or copy, only to enable.
        msg_info "using the system-wide extensions in $(system_extensions_dir) (no download)"
        enable_extensions "${EXTENSION_UUIDS[@]}"
        warn_blur_my_shell
        return 0
    fi
    if [[ -n "$EXTENSIONS_DIR" ]]; then
        repo="$(readlink -f -- "$EXTENSIONS_DIR")"
        ((DRY_RUN)) || [[ -x "$repo/scripts/install.sh" ]] || die "$EXTENSIONS_DIR is not an m3e-gnome-extensions checkout (scripts/install.sh missing)"
    else
        fetch_git m3e-gnome-extensions "$EXT_URL" "$EXT_REV"
        repo="$SRC_DIR/m3e-gnome-extensions"
    fi
    if ((DRY_RUN)); then msg_info "[dry-run] build the extensions with $repo/scripts/install.sh and copy them to $EXT_DEST"; return 0; fi
    make_tmp; stage="$REPLY"
    bash "$repo/scripts/install.sh" --dest "$stage" >/dev/null
    for d in "$stage"/*/; do
        uuid="$(basename -- "$d")"
        put_tree "${d%/}" "$EXT_DEST/$uuid"
        uuids+=("$uuid")
    done
    ((${#uuids[@]})) || die "the extensions repository installed nothing"
    enable_extensions "${uuids[@]}"
    warn_blur_my_shell
}

warn_blur_my_shell() {
    if [[ "$(python3 "$EXT_HELPER_PY" list)" == *blur-my-shell@aunetx* ]]; then
        msg_warn "Blur my Shell is enabled: the M3E theme uses tinted surfaces instead of blur and the two can conflict"
    fi
}
