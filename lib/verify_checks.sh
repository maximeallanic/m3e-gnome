# shellcheck shell=bash
# Read-only checks used by verify.sh. Requires common.sh, settings.sh (gs_get), pins.sh, the SELECTED/step_enabled
# helpers and REPO_ROOT. Each check prints OK, WARN or FAIL; WARN is a state that fixes itself (e.g. an extension
# the running Shell has not discovered yet) and only fails with --strict.

V_OK=0; V_FAIL=0; V_WARN=0

v_ok() { printf 'OK     %s\n' "$*"; V_OK=$((V_OK + 1)); }
v_fail() { printf 'FAIL   %s\n' "$*"; V_FAIL=$((V_FAIL + 1)); }
v_warn() { printf 'WARN   %s\n' "$*"; V_WARN=$((V_WARN + 1)); }
# v_if "ok message" "failure message" command...: OK when the command succeeds, FAIL otherwise.
v_if() {
    local okmsg="$1" failmsg="$2"
    shift 2
    if "$@" >/dev/null 2>&1; then v_ok "$okmsg"; else v_fail "$failmsg"; fi
}
shorten() { printf '%s\n' "${1/#$HOME/\~}"; }

v_equal() { # schema key expected
    local v
    if ! v="$(gs_get "$1" "$2" 2>/dev/null)"; then v_fail "$2: key not readable"; return; fi
    if [[ "$v" == "$3" ]]; then v_ok "$2 = $3"; else v_fail "$2 = $v (expected $3)"; fi
}

v_same() { # repo-file installed-file
    if [[ ! -e "$2" ]]; then v_fail "missing: $(shorten "$2")"
    elif cmp -s -- "$1" "$2"; then v_ok "up to date: $(shorten "$2")"
    else v_fail "differs from the repository: $(shorten "$2")"; fi
}

v_tree_same() { # repo-dir installed-dir [rsync excludes...]
    local src="$1" dest="$2" diff
    shift 2
    if [[ ! -d "$dest" ]]; then v_fail "missing: $(shorten "$dest")"; return; fi
    diff="$(rsync -rlcn --delete --itemize-changes "$@" -- "$src/" "$dest/")"
    if [[ -z "$diff" ]]; then v_ok "up to date: $(shorten "$dest")"; else v_fail "differs from the repository: $(shorten "$dest")"; fi
}

v_rendered() { # file (must exist, be non-empty and contain no unrendered {{ }} placeholder)
    if [[ ! -s "$1" ]]; then v_fail "not rendered: $(shorten "$1")"
    elif grep -q '{{' "$1"; then v_fail "unrendered placeholders in $(shorten "$1")"
    else v_ok "rendered: $(shorten "$1")"; fi
}

check_manifest() {
    local t p missing=0 n=0
    if [[ ! -f "$STATE_DIR/manifest" ]]; then v_fail "no manifest: nothing installed by install.sh ($STATE_DIR/manifest)"; return; fi
    while IFS=$'\t' read -r t p; do
        [[ "$t" == D ]] && continue
        n=$((n + 1))
        if [[ ! -e "$p" && ! -L "$p" ]]; then v_fail "listed in the manifest but missing: $(shorten "$p")"; missing=1; fi
    done <"$STATE_DIR/manifest"
    ((missing)) || v_ok "manifest: all $n recorded paths exist"
}

check_settings() {
    local I=org.gnome.desktop.interface cursor=Googlebook
    [[ "${CURSOR_STYLE:-black}" == white ]] && cursor=Googlebook-White
    step_enabled gtk-theme && { v_equal $I gtk-theme Material-Gnome
        v_equal org.gnome.desktop.wm.preferences button-layout 'appmenu:minimize,maximize,close'; }
    step_enabled icons && v_equal $I icon-theme Material-Symbols
    step_enabled cursor && v_equal $I cursor-theme "$cursor"
    step_enabled font && v_equal $I font-name 'Google Sans Flex 10.5'
    step_enabled sounds && v_equal org.gnome.desktop.sound theme-name Materia
    if step_enabled palette; then
        if gs_schema_exists org.gnome.shell.extensions.user-theme; then
            v_equal org.gnome.shell.extensions.user-theme name M3E-Shell
        else
            v_fail "GNOME 'User Themes' extension not installed: the Shell theme cannot load ($(user_theme_hint))"
        fi
    fi
}

check_files() {
    local f
    if step_enabled gtk-theme; then
        if [[ -f "$THEMES_DIR/Material-Gnome/.m3e-rev" && "$(cat "$THEMES_DIR/Material-Gnome/.m3e-rev")" == "$MATGNOME_REV" ]]; then
            v_ok "Material-Gnome at the pinned commit ${MATGNOME_REV:0:12}"
        else v_fail "Material-Gnome is not at the pinned commit ${MATGNOME_REV:0:12} (re-run ./install.sh)"; fi
        if grep -qE 'font-weight: *(bold|bolder|[6-9]00)' "$THEMES_DIR"/Material-Gnome/gtk-4.0/gtk*.css 2>/dev/null; then
            v_fail "GTK 4 theme still contains bold weights"
        else v_ok "GTK 4 theme has no bold weights"; fi
    fi
    if step_enabled icons; then
        for f in Papirus/index.theme Papirus-Dark/index.theme Papirus-Symbolic/index.theme Material-Symbols/index.theme; do
            v_if "present: $(shorten "$ICONS_DIR/$f")" "missing: $(shorten "$ICONS_DIR/$f")" test -f "$ICONS_DIR/$f"
        done
        v_tree_same "$REPO_ROOT/theme/icons/Material-Symbols" "$ICONS_DIR/Material-Symbols" --exclude icon-theme.cache
        v_if "present: $(shorten "$BIN_DIR/papirus-folders")" "missing: $(shorten "$BIN_DIR/papirus-folders")" test -x "$BIN_DIR/papirus-folders"
    fi
    if step_enabled cursor; then
        local theme=Googlebook
        [[ "${CURSOR_STYLE:-black}" == white ]] && theme=Googlebook-White
        v_if "cursor theme $theme built" "cursor theme $theme missing" test -e "$ICONS_DIR/$theme/cursors/default"
        v_if "default X11 cursor: $theme" "$HOME/.icons/default/index.theme does not inherit $theme" \
            grep -qx "Inherits=$theme" "$HOME/.icons/default/index.theme"
    fi
    if step_enabled sounds; then
        v_if "sound theme Materia installed" "sound theme Materia missing" test -f "$DATA_HOME/sounds/Materia/index.theme"
    fi
    if step_enabled font; then
        if [[ "$(fc-list : family 2>/dev/null)" == *'Google Sans Flex'* ]]; then v_ok "font Google Sans Flex installed"
        else v_fail "font Google Sans Flex not found by fontconfig"; fi
    fi
}

check_palette_files() {
    local f name
    for f in "$REPO_ROOT"/theme/overrides/*; do
        name="$(basename "$f")"
        [[ "$name" == README.md ]] || v_same "$f" "$M3E_CONFIG/overrides/$name"
    done
    v_same "$REPO_ROOT/theme/motion/gtk/m3e-gtk4-motion.css" "$M3E_CONFIG/overrides/m3e-gtk4-motion.css"
    for f in "$REPO_ROOT"/theme/shell/m3e-shell/*.css; do v_same "$f" "$M3E_CONFIG/shell/$(basename "$f")"; done
    v_same "$REPO_ROOT/theme/shell/m3e-extensions-template.css" "$M3E_CONFIG/m3e-extensions-template.css"
    v_same "$REPO_ROOT/theme/matugen/config.toml" "$MATUGEN_DIR/config.toml"
    v_same "$REPO_ROOT/theme/matugen/palette.json" "$MATUGEN_DIR/palette.json"
    for f in material-sync material-sync-watch material-palette; do v_same "$REPO_ROOT/theme/bin/$f" "$BIN_DIR/$f"; done
    v_same "$REPO_ROOT/theme/systemd/material-sync.service" "$CONFIG_HOME/systemd/user/material-sync.service"
    v_if "present: $(shorten "$LIB_DIR/material-palette/palette.mjs")" "missing: $(shorten "$LIB_DIR/material-palette/palette.mjs")" \
        test -f "$LIB_DIR/material-palette/palette.mjs"
    local m
    m="$(command -v matugen || true)"
    [[ -z "$m" && -x "$BIN_DIR/matugen" ]] && m="$BIN_DIR/matugen"
    if [[ -n "$m" ]] && matugen_version_ok "$m"; then v_ok "matugen $("$m" --version | cut -d' ' -f2) at $(shorten "$m")"
    else v_fail "matugen $MATUGEN_MIN_VERSION or newer not found"; fi
}

check_rendered() {
    local f parts=() shell_css="$THEMES_DIR/M3E-Shell/gnome-shell/gnome-shell.css"
    v_if "GTK 4 palette rendered" "GTK 4 colors.css has no --primary (run material-sync --force)" \
        grep -q -- '--primary: #' "$THEMES_DIR/Material-Gnome/gtk-4.0/colors.css"
    v_if "GTK 3 palette rendered" "GTK 3 colors.css has no primary colour" \
        grep -q '@define-color primary #' "$THEMES_DIR/Material-Gnome/gtk-3.0/colors.css"
    for f in "$REPO_ROOT"/theme/shell/m3e-shell/*.css; do
        v_rendered "$M3E_CACHE/shell/$(basename "$f")"
        parts+=("$M3E_CACHE/shell/$(basename "$f")")
    done
    v_rendered "$shell_css"
    if [[ -s "$shell_css" ]]; then
        if cat "${parts[@]}" 2>/dev/null | cmp -s - "$shell_css"; then v_ok "M3E-Shell stylesheet = concatenation of the rendered parts"
        else v_fail "M3E-Shell stylesheet is not the concatenation of the rendered parts (run material-sync --force)"; fi
        v_if "M3E-Shell has the no-bold rule" "M3E-Shell lacks the no-bold rule" grep -q 'font-weight: normal !important' "$shell_css"
    fi
    v_rendered "$M3E_CONFIG/m3e-extensions.css"
    v_rendered "$M3E_CONFIG/overrides/chrome-dark-gtk4.css"
    f="$DATA_HOME/org.gnome.Ptyxis/palettes/material.palette"
    v_rendered "$f"
    if [[ -s "$f" ]]; then
        v_if "Ptyxis palette has a [Light] section" "Ptyxis palette has no [Light] section" grep -qx '\[Light\]' "$f"
        v_if "Ptyxis palette has a [Dark] section" "Ptyxis palette has no [Dark] section" grep -qx '\[Dark\]' "$f"
    fi
    check_gtk_imports
}

check_gtk_imports() {
    local f a b
    for f in gtk-4.0/gtk.css gtk-4.0/gtk-dark.css gtk-3.0/gtk.css; do
        if [[ -L "$CONFIG_HOME/$f" || ! -f "$CONFIG_HOME/$f" ]]; then v_fail "$f is not a regular file written by the installer"; continue; fi
        case "$f" in gtk-4.0/*) a=m3e-gtk4.css; b=window-buttons-gtk4.css ;; *) a=m3e-gtk3.css; b=window-buttons-gtk3.css ;; esac
        local la lb
        la="$(grep -n -- "$a" "$CONFIG_HOME/$f" | head -n 1 | cut -d: -f1)"
        lb="$(grep -n -- "$b" "$CONFIG_HOME/$f" | head -n 1 | cut -d: -f1)"
        if [[ -n "$la" && -n "$lb" && "$la" -lt "$lb" ]]; then v_ok "$f imports $a before $b"
        else v_fail "$f: $a missing or imported after $b"; fi
    done
}

check_extensions() {
    local u enabled state d="$EXT_DEST"
    enabled="$(python3 "$LIB/enabled_extensions.py" list)"
    for u in "${EXTENSION_UUIDS[@]}"; do
        if [[ -f "$d/$u/metadata.json" ]] && grep -q "\"$u\"" "$d/$u/metadata.json"; then v_ok "extension installed: $u"
        elif use_system_extensions; then v_ok "extension installed system-wide: $u"
        else v_fail "extension missing or without matching metadata.json: $u"; continue; fi
        if grep -qxF "$u" <<<"$enabled"; then v_ok "extension enabled: $u"; else v_fail "extension not enabled: $u"; continue; fi
        state="$(gnome-extensions info "$u" 2>/dev/null | sed -n 's/^ *State: *//p')"
        case "$state" in
            ACTIVE|ENABLED) v_ok "extension running in the Shell: $u" ;;
            *) v_warn "extension $u is not loaded by the running Shell (state: ${state:-unknown}): log out and back in" ;;
        esac
    done
    if grep -qxF "$USER_THEME_UUID" <<<"$enabled"; then v_ok "User Themes extension enabled"
    elif step_enabled palette; then v_fail "User Themes extension is not enabled"; fi
}

check_service() {
    if systemctl --user is-active -q material-sync.service; then v_ok "material-sync.service is active"
    else v_fail "material-sync.service is not active (systemctl --user status material-sync.service)"; fi
}
