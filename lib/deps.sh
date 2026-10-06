# shellcheck shell=bash
# Dependency detection and per-distribution install commands (Debian/Ubuntu apt, Fedora dnf, Arch pacman,
# openSUSE zypper), chosen from os-release ID / ID_LIKE. Nothing is installed unless --install-deps is given, and then
# only after confirmation. Requires common.sh.

# command | apt | dnf | pacman | zypper
DEP_TABLE='
git|git|git|git|git
rsync|rsync|rsync|rsync|rsync
curl|curl|curl|curl|curl
python3|python3|python3|python3|python3
sha256sum|coreutils|coreutils|coreutils|coreutils
gsettings|libglib2.0-bin|glib2|glib2|glib2-tools
dconf|dconf-cli|dconf|dconf|dconf
gnome-extensions|gnome-shell|gnome-shell|gnome-shell|gnome-shell
fc-cache|fontconfig|fontconfig|fontconfig|fontconfig
node|nodejs|nodejs|nodejs|nodejs-default
npm|npm|npm|npm|npm-default
ffmpeg|ffmpeg|ffmpeg-free|ffmpeg|ffmpeg
rsvg-convert|librsvg2-bin|librsvg2-tools|librsvg|rsvg-convert
meson|meson|meson|meson|meson
ninja|ninja-build|ninja-build|ninja|ninja
gtk-update-icon-cache|libgtk-3-bin|gtk-update-icon-cache|gtk3|gtk3-tools
'
# GNOME Shell "User Themes" extension (required to load the Shell theme), per family.
user_theme_pkg() {
    case "$1" in
        debian|arch) echo gnome-shell-extensions ;;
        fedora|suse) echo gnome-shell-extension-user-theme ;;
    esac
}

pkg_for() { # family command -> package name ('' when unknown)
    local family="$1" cmd="$2" col c p
    case "$family" in debian) col=2 ;; fedora) col=3 ;; arch) col=4 ;; suse) col=5 ;; *) return 0 ;; esac
    while IFS='|' read -r c p; do
        [[ "$c" == "$cmd" ]] && { printf '%s\n' "$p"; return 0; }
    done < <(printf '%s' "$DEP_TABLE" | cut -d'|' -f1,"$col")
}

install_cmd() { # family assume-yes(0|1) packages... -> the command, one word per line
    local family="$1" yes="$2" flags=()
    shift 2
    case "$family" in
        debian) ((yes)) && flags=(-y); printf '%s\n' sudo apt-get install --no-install-recommends "${flags[@]}" "$@" ;;
        fedora) ((yes)) && flags=(-y); printf '%s\n' sudo dnf install "${flags[@]}" "$@" ;;
        arch) ((yes)) && flags=(--noconfirm); printf '%s\n' sudo pacman -S --needed "${flags[@]}" "$@" ;;
        suse) ((yes)) && flags=(--non-interactive); printf '%s\n' sudo zypper "${flags[@]}" install "$@" ;;
    esac
}

# Commands each selected step needs. gtk-update-icon-cache is not one of them: without it the icon themes work, only
# GTK starts slower (steps_theme.sh warns).
deps_required() {
    local cmds=(git curl python3 sha256sum gsettings dconf gnome-extensions)
    step_enabled gtk-theme && cmds+=(rsync)
    step_enabled icons && cmds+=(rsync)
    step_enabled cursor && cmds+=(rsvg-convert)
    step_enabled sounds && cmds+=(meson ninja)
    step_enabled font && cmds+=(fc-cache)
    if step_enabled palette; then
        cmds+=(node ffmpeg)
        # npm only builds the palette bundle; a prebuilt one (the .deb) needs none.
        if ! has_prebuilt_palette; then cmds+=(npm); fi
    fi
    # The system-wide extension package is only enabled, never copied.
    if step_enabled extensions && ! use_system_extensions; then cmds+=(rsync); fi
    printf '%s\n' "${cmds[@]}" | sort -u
}

DEPS_PACKAGES=()

# Oldest Python 3 the project's scripts run on (str.removeprefix, 3.9 type syntax). Debian 11+, Ubuntu 22.04+,
# Fedora, Arch and openSUSE Leap 15.5+ ship 3.9 or newer; Ubuntu 20.04 (3.8) and RHEL 8 (3.6) do not.
PYTHON_MIN=3.9

check_python_version() {
    have python3 || return 0 # reported as a missing tool
    python3 -c 'import sys; v = tuple(map(int, sys.argv[1].split("."))); sys.exit(sys.version_info[:2] < v)' "$PYTHON_MIN" ||
        die "python3 $(python3 -c 'import platform; print(platform.python_version())') is too old: Python $PYTHON_MIN or newer is required"
}

# Report missing tools with the exact install command; return 1 when a required one is missing.
check_deps() {
    local cmd pkg family missing=()
    family="$(os_family)"
    check_python_version
    while IFS= read -r cmd; do have "$cmd" || missing+=("$cmd"); done < <(deps_required)
    if ((${#missing[@]} == 0)); then
        msg_info "dependencies: all present"
        return 0
    fi
    msg_warn "missing tools: ${missing[*]}"
    if [[ "$family" == unknown ]]; then
        msg_info "unrecognised distribution (see /etc/os-release): install the packages that provide: ${missing[*]}"
        return 1
    fi
    DEPS_PACKAGES=()
    for cmd in "${missing[@]}"; do
        pkg="$(pkg_for "$family" "$cmd")"
        [[ -n "$pkg" ]] && DEPS_PACKAGES+=("$pkg")
    done
    mapfile -t DEPS_PACKAGES < <(printf '%s\n' "${DEPS_PACKAGES[@]}" | sort -u)
    msg_info "install them with:"
    msg_info "  $(install_cmd "$family" 0 "${DEPS_PACKAGES[@]}" | xargs printf '%q ')"
    return 1
}

# Run the command printed by check_deps, after confirmation.
install_deps() {
    local cmd
    mapfile -t cmd < <(install_cmd "$(os_family)" "$ASSUME_YES" "${DEPS_PACKAGES[@]}")
    msg_info "about to run: $(printf '%q ' "${cmd[@]}")"
    confirm "Run it now (needs sudo)?" || die "dependencies not installed"
    run "${cmd[@]}"
}

user_theme_hint() { # prints the command that installs the User Themes extension, or a generic sentence
    local family pkg
    family="$(os_family)"
    pkg="$(user_theme_pkg "$family")"
    if [[ -n "$pkg" ]]; then
        install_cmd "$family" 0 "$pkg" | xargs printf '%q '
        echo
    else
        echo "install the GNOME Shell 'User Themes' extension from your distribution"
    fi
}
