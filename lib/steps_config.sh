# shellcheck shell=bash
# The palette engine: templates, matugen config, palette tool, scripts, user service, GTK imports, first render.
# Requires common.sh, manifest.sh, matugen.sh, settings.sh; REPO_ROOT and option variables from install.sh.

SERVICE=material-sync.service

step_palette_files() {
    msg_step "Palette engine: matugen, templates, scripts"
    mkdir_owned "$M3E_CACHE"
    ensure_matugen
    claim_tree "$M3E_CONFIG"
    mkdir_owned "$M3E_CONFIG"
    # Templates: matugen renders ~/.config/m3e-gnome/{shell,overrides}/* (config.toml says so) into the caches and
    # into the theme directories.
    put_tree "$REPO_ROOT/theme/shell/m3e-shell" "$M3E_CONFIG/shell"
    put_tree "$REPO_ROOT/theme/overrides" "$M3E_CONFIG/overrides" --exclude README.md
    put_file "$REPO_ROOT/theme/motion/gtk/m3e-gtk4-motion.css" "$M3E_CONFIG/overrides/m3e-gtk4-motion.css" 644
    put_file "$REPO_ROOT/theme/shell/m3e-extensions-template.css" "$M3E_CONFIG/m3e-extensions-template.css" 644
    # Our own matugen directory: a user's ~/.config/matugen/ is neither read nor replaced (the scripts pass --config).
    put_file "$REPO_ROOT/theme/matugen/config.toml" "$MATUGEN_DIR/config.toml" 644
    put_file "$REPO_ROOT/theme/matugen/palette.json" "$MATUGEN_DIR/palette.json" 644

    # Palette computation (2025 colour spec): official material-color-utilities, pinned by package-lock.json.
    mkdir_owned "$LIB_DIR/material-palette"
    claim "$LIB_DIR/material-palette/palette.mjs"
    m_record F "$LIB_DIR/material-palette/palette.mjs"
    if has_prebuilt_palette; then
        run install -m 644 -- "$REPO_ROOT/$PREBUILT_PALETTE_REL" "$LIB_DIR/material-palette/palette.mjs"
    else
        # npm's cache goes into our cache directory: nothing may be created in ~/.npm.
        run env npm_config_cache="$M3E_CACHE/npm" bash "$REPO_ROOT/tools/material-palette/build.sh" "$LIB_DIR/material-palette/palette.mjs" >/dev/null
    fi

    local f
    for f in material-sync material-sync-watch material-palette; do
        put_file "$REPO_ROOT/theme/bin/$f" "$BIN_DIR/$f" 755
    done
    put_file "$REPO_ROOT/theme/systemd/$SERVICE" "$CONFIG_HOME/systemd/user/$SERVICE" 644
    write_gtk_imports
}

# GTK 3 and GTK 4 / libadwaita (and Chrome, which reads GTK 4) load these user stylesheets: the base theme, then the
# M3E overrides, then the title-bar geometry and the no-bold rules, in that cascade order.
write_gtk_imports() {
    local o="file://$HOME_URL/.config/m3e-gnome/overrides" t="file://$HOME_URL/.themes/Material-Gnome" f
    for f in gtk.css gtk-dark.css; do
        put_text "$CONFIG_HOME/gtk-4.0/$f" 644 <<EOT
@import url("$t/gtk-4.0/$f");
@import url("$o/m3e-gtk4-motion.css");
@import url("$o/m3e-gtk4.css");
@import url("$o/window-buttons-gtk4.css");
@import url("$o/no-bold-gtk4.css");
EOT
    done
    put_link "$THEMES_DIR/Material-Gnome/gtk-4.0/colors.css" "$CONFIG_HOME/gtk-4.0/colors.css"
    put_text "$CONFIG_HOME/gtk-3.0/gtk.css" 644 <<EOT
@import url("$o/m3e-gtk3.css");
@import url("$o/window-buttons-gtk3.css");
@import url("$o/no-bold-gtk3.css");
EOT
}

fallback_color() { # seed colour used when there is no wallpaper to read (installed settings, else the repository's)
    local file="$MATUGEN_DIR/palette.json"
    [[ -f "$file" ]] || file="$REPO_ROOT/theme/matugen/palette.json"
    python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["fallback_color"])' "$file"
}

step_palette_render() {
    msg_step "First palette"
    local mode=dark shell_css="$THEMES_DIR/M3E-Shell/gnome-shell/gnome-shell.css"
    case "$COLOR_SCHEME" in
        light) mode=light ;;
        keep) [[ "$(gs_get org.gnome.desktop.interface color-scheme)" == prefer-dark ]] || mode=light ;;
    esac
    # Parents of files that the matugen config writes: created here so that they are recorded.
    mkdir_owned "$HOME/.local/share/org.gnome.Ptyxis/palettes"
    mkdir_owned "$M3E_CACHE/shell"
    mkdir_owned "$THEMES_DIR/M3E-Shell/gnome-shell"
    if ((DRY_RUN)); then
        msg_info "[dry-run] material-sync --force (palette from the wallpaper, fallback colour otherwise)"
        return 0
    fi
    local stamp
    make_tmp; stamp="$REPLY/stamp"
    touch -d '2 seconds ago' -- "$stamp"
    PATH="$BIN_DIR:$PATH" "$BIN_DIR/material-sync" --force ||
        die "material-sync failed (see $CACHE_HOME/material-sync/material-sync.log)"
    if [[ ! "$shell_css" -nt "$stamp" ]]; then
        # No wallpaper image could be read (material-sync exits 0 and renders nothing): seed from the fallback colour.
        msg_info "no wallpaper image found: using the fallback colour $(fallback_color)"
        PATH="$BIN_DIR:$PATH" "$BIN_DIR/material-palette" --color "$(fallback_color)" --mode "$mode" \
            --matugen-config "$MATUGEN_DIR/config.toml" || die "material-palette failed"
    fi
    [[ -s "$shell_css" ]] || die "no Shell stylesheet was rendered: $shell_css"
    record_generated
}

# Everything the render created that is not inside a tree we already own.
record_generated() {
    local f
    record_file "$THEMES_DIR/M3E-Shell/gnome-shell/gnome-shell.css"
    record_file "$DATA_HOME/org.gnome.Ptyxis/palettes/material.palette"
    for f in matugen-papirus-folders.txt matugen-gnome-accent.txt papirus-folders.log; do
        record_file "$CACHE_HOME/$f"
    done
    record_tree "$CACHE_HOME/material-sync"
    record_tree "$M3E_CACHE"
    record_tree "$M3E_CONFIG"
}

step_palette_service() {
    msg_step "Palette service ($SERVICE)"
    run systemctl --user daemon-reload
    run systemctl --user enable --now "$SERVICE"
    state_set service enabled
}
