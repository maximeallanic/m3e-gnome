# shellcheck shell=bash
# GDM login screen, user side: prepare DATA only. Runs as the user, writes only into a private temporary directory.
# Nothing here is ever executed by root: the root helper (gdm/m3e-gdm) treats the directory as untrusted input.
#   theme.css       the M3E-Shell stylesheet rendered in the dark palette from the chosen seed (matugen, the repo templates)
#   background.png  the wallpaper blurred (ffmpeg), optional
#   greeter.conf    icon theme, cursor theme, font name for the dconf database
#   assets/         icon theme, cursor theme and font, symbolic links resolved into regular files
# Requires common.sh, manifest.sh helpers (make_tmp), settings.sh (gs_get) and the globals of install.sh.

GDM_BLUR_WIDTH=1920
GDM_BLUR_SIGMA=30
GDM_IMAGE=''          # --gdm-image: seed and background (default: the current dark wallpaper)

# Wallpaper file of the session ('' when it is not a plain image file).
gdm_wallpaper_file() {
    local uri path
    uri="$(gs_get org.gnome.desktop.background picture-uri-dark 2>/dev/null || true)"
    [[ -n "$uri" ]] || uri="$(gs_get org.gnome.desktop.background picture-uri 2>/dev/null || true)"
    [[ "$uri" == file://* ]] || return 0
    path="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1][7:]))' "$uri")"
    [[ -f "$path" ]] || return 0
    # By content, not by extension: GNOME and material-sync keep the wallpaper in files such as ~/.config/background.
    python3 - "$path" <<'PY' && printf '%s' "$path"
import sys
head = open(sys.argv[1], 'rb').read(16)
ok = (head.startswith(b'\x89PNG\r\n\x1a\n') or head.startswith(b'\xff\xd8\xff') or head.startswith(b'BM')
      or (head[:4] == b'RIFF' and head[8:12] == b'WEBP'))
sys.exit(0 if ok else 1)
PY
    return 0
}

# Render the dark Shell stylesheet from the repo templates into $1 (a file).
gdm_render_css() { # out-file seed-args...
    local out="$1" tmp f n=0 cfg
    shift
    local palette="$BIN_DIR/material-palette"
    [[ -x "$palette" ]] || die "material-palette is not installed ($palette): run ./install.sh first (the palette engine step)"
    make_tmp; tmp="$REPLY"
    mkdir -p -- "$tmp/parts"
    [[ "$tmp" != *\'* ]] || die "temporary directory name contains a quote"
    cfg="$tmp/config.toml"
    printf '[config]\nversion_check = false\n' >"$cfg"
    for f in "$REPO_ROOT"/theme/shell/m3e-shell/*.css; do
        [[ "$f" != *\'* ]] || die "repository path contains a quote: $f"
        printf "\n[templates.gdm-%02d]\ninput_path = '%s'\noutput_path = '%s/parts/%s'\nindex = %d\n" \
            "$n" "$f" "$tmp" "$(basename -- "$f")" "$((10 + n))" >>"$cfg"
        n=$((n + 1))
    done
    PATH="$BIN_DIR:$PATH" "$palette" "$@" --mode dark --matugen-config "$cfg" >/dev/null ||
        die "material-palette failed while rendering the greeter stylesheet"
    : >"$out"
    for f in "$REPO_ROOT"/theme/shell/m3e-shell/*.css; do
        [[ -s "$tmp/parts/$(basename -- "$f")" ]] || die "part not rendered: $(basename -- "$f")"
        cat -- "$tmp/parts/$(basename -- "$f")" >>"$out"
        printf '\n' >>"$out"
    done
    ! grep -qF '{{' "$out" || die "unrendered placeholders in the greeter stylesheet"
    # The helper checks the stylesheet token by token and has no use for comments: strip them here (tokenizer, not regex).
    python3 -I -B "$REPO_ROOT/gdm/ingest.py" strip-css "$out" "$out.stripped" || die "the rendered stylesheet is not valid CSS"
    mv -- "$out.stripped" "$out"
}

# Blurred background: the image is scaled to 1920 px wide and Gaussian-blurred by ffmpeg (adopted, not reimplemented).
gdm_blur() { # image out.png
    have ffmpeg || { msg_warn "ffmpeg not found: the login screen gets a plain background instead of the blurred wallpaper"; return 1; }
    ffmpeg -nostdin -v error -y -i "$1" -frames:v 1 \
        -vf "scale=${GDM_BLUR_WIDTH}:-2:flags=lanczos,gblur=sigma=${GDM_BLUR_SIGMA}:steps=3" "$2" ||
        die "ffmpeg could not blur $1"
}

# Copy a theme directory with every symbolic link resolved to a regular file (the root helper accepts no links).
gdm_copy_resolved() { # src dst
    mkdir -p -- "$(dirname -- "$2")"
    cp -rL -- "$1" "$2"
}

gdm_stage_assets() { # data-dir ; sets GDM_FONT_NAME
    local data="$1" cursor=Googlebook font_dir="$DATA_HOME/fonts/GoogleSansFlex"
    [[ "$CURSOR_STYLE" == white ]] && cursor=Googlebook-White
    GDM_CURSOR="$cursor"
    if [[ -f "$ICONS_DIR/Material-Symbols/index.theme" ]]; then
        mkdir -p -- "$data/assets/icons/Material-Symbols"
        gdm_copy_resolved "$ICONS_DIR/Material-Symbols/symbolic" "$data/assets/icons/Material-Symbols/symbolic"
        # Papirus-Symbolic (its fallback) is not installed for the greeter: fall back to Adwaita and hicolor.
        sed 's/^Inherits=.*/Inherits=Adwaita,hicolor/' "$ICONS_DIR/Material-Symbols/index.theme" >"$data/assets/icons/Material-Symbols/index.theme"
        GDM_ICON_THEME=Material-Symbols
    else
        msg_warn "Material-Symbols is not installed: the greeter keeps the default icon theme"
        GDM_ICON_THEME=Adwaita
    fi
    if [[ -d "$ICONS_DIR/$cursor/cursors" ]]; then
        gdm_copy_resolved "$ICONS_DIR/$cursor" "$data/assets/icons/$cursor"
    else
        msg_warn "cursor theme $cursor is not installed: the greeter keeps the default cursor"
        GDM_CURSOR=Adwaita
    fi
    GDM_FONT_NAME='Cantarell 11'
    if compgen -G "$font_dir/*.ttf" >/dev/null; then
        mkdir -p -- "$data/assets/fonts/GoogleSansFlex"
        cp -L -- "$font_dir"/*.ttf "$font_dir"/OFL.txt "$data/assets/fonts/GoogleSansFlex/"
        GDM_FONT_NAME='Google Sans Flex 10.5'
    else
        msg_warn "Google Sans Flex is not installed: the greeter keeps its default font"
    fi
}

# gdm_prepare DATA_DIR : builds the whole input directory. Returns 1 (after a message) when something is missing and
# the run is a dry run; dies otherwise.
gdm_prepare() {
    local data="$1" image seed_args seed_label
    mkdir -m 700 -- "$data"
    image="${GDM_IMAGE:-$(gdm_wallpaper_file)}"
    if [[ -n "$image" ]]; then
        [[ -f "$image" ]] || die "--gdm-image: not a file: $image"
        seed_args=(--image "$image"); seed_label=image
    else
        seed_args=(--color "$(fallback_color)"); seed_label="$(fallback_color)"
        msg_info "no usable wallpaper image: seed colour $seed_label and a plain background"
    fi
    gdm_render_css "$data/theme.css" "${seed_args[@]}"
    if [[ -n "$image" ]]; then gdm_blur "$image" "$data/background.png" || rm -f -- "$data/background.png"; fi
    gdm_stage_assets "$data"
    printf 'icon_theme=%s\ncursor_theme=%s\nfont_name=%s\nseed=%s\n' "$GDM_ICON_THEME" "$GDM_CURSOR" "$GDM_FONT_NAME" "${seed_label//[^A-Za-z0-9#]/_}" >"$data/greeter.conf"
    python3 -I -B "$REPO_ROOT/gdm/ingest.py" check "$data" || die "the prepared greeter data does not pass the safety checks"
}
