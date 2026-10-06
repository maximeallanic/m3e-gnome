# shellcheck shell=bash
# Shared helpers: logging, dry-run wrapper, paths, temp directories, OS detection.
# Sourced by install.sh, uninstall.sh and verify.sh; never executed.

# Tool output is parsed in several places (gsettings, gnome-shell --version, ...): force the C locale so parsing does
# not depend on the user's language. User-facing messages of this project are English only.
export LC_ALL=C
export LANGUAGE=C
# The scripts run from the repository directory, which is read-only when installed by the .deb: never write bytecode
# caches (tools/*.py import their siblings) next to the sources.
export PYTHONDONTWRITEBYTECODE=1

# The companion GNOME Shell extensions (m3e-gnome-extensions).
EXTENSION_UUIDS=(m3e-motion@maximeallanic.github.io m3e-extensions@maximeallanic.github.io status-bar@maximeallanic.github.io)

# Print the first directory of M3E_SYSTEM_EXT_DIRS (default: the system-wide extension directories) that holds all
# three companion extensions, e.g. /usr/share/gnome-shell/extensions after `apt install gnome-shell-extension-m3e`.
# The variable is a test seam (tests point it at a fake root, never at the real /usr).
system_extensions_dir() {
    local d u ok
    for d in ${M3E_SYSTEM_EXT_DIRS-/usr/local/share/gnome-shell/extensions /usr/share/gnome-shell/extensions}; do
        ok=1
        for u in "${EXTENSION_UUIDS[@]}"; do
            [[ -f "$d/$u/metadata.json" && -f "$d/$u/extension.js" ]] || ok=0
        done
        if ((ok)); then printf '%s\n'  "$d"; return 0; fi
    done
    return 1
}
# True when the extensions step should only enable the system-wide copies (an explicit --extensions-dir wins).
use_system_extensions() { [[ -z "${EXTENSIONS_DIR:-}" ]] && system_extensions_dir >/dev/null; }

# True when the repository ships the prebuilt palette bundle (the .deb does): no npm needed at install time.
PREBUILT_PALETTE_REL=tools/material-palette/dist/palette.mjs
has_prebuilt_palette() { [[ -n "${REPO_ROOT:-}" && -f "$REPO_ROOT/$PREBUILT_PALETTE_REL" ]]; }

M3E_VERSION=0.1.0
DRY_RUN=0
WARNINGS=0

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    C_BOLD=$'\033[1m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_GREEN=$'\033[32m'; C_OFF=$'\033[0m'
else
    C_BOLD=''; C_RED=''; C_YELLOW=''; C_GREEN=''; C_OFF=''
fi

msg_step() { printf '\n%s== %s%s\n' "$C_BOLD" "$*" "$C_OFF"; }
msg_info() { printf '   %s\n' "$*"; }
msg_warn() { printf '%swarning:%s %s\n' "$C_YELLOW" "$C_OFF" "$*" >&2; WARNINGS=$((WARNINGS + 1)); }
die() { printf '%serror:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; exit 1; }

# Resolve the repository root from the script that sources us (follows symlinks).
resolve_repo_root() {
    local src="${BASH_SOURCE[1]}"
    src="$(readlink -f -- "$src")"
    dirname -- "$(dirname -- "$src")"
}

# User directories. The matugen config shipped by the theme (and the Ptyxis/Papirus hooks in it) addresses
# ~/.config, ~/.cache and ~/.local/share literally, so only the default XDG layout is supported.
init_paths() {
    : "${HOME:?HOME is not set}"
    [[ "$HOME" == /* ]] || die "HOME must be an absolute path (got '$HOME')"
    local v
    for v in CONFIG:.config CACHE:.cache DATA:.local/share; do
        local var="XDG_${v%%:*}_HOME" want="$HOME/${v#*:}"
        [[ -z "${!var:-}" || "${!var}" == "$want" ]] ||
            die "$var=${!var} is not supported: the theme's matugen config uses ~/${v#*:} literally. Unset $var or point it there"
    done
    DATA_HOME="$HOME/.local/share"
    CONFIG_HOME="$HOME/.config"
    CACHE_HOME="$HOME/.cache"
    BIN_DIR="$HOME/.local/bin"
    LIB_DIR="$HOME/.local/lib"
    THEMES_DIR="$HOME/.themes"
    ICONS_DIR="$DATA_HOME/icons"
    STATE_DIR="$DATA_HOME/m3e-gnome"
    M3E_CONFIG="$CONFIG_HOME/m3e-gnome"
    MATUGEN_DIR="$M3E_CONFIG/matugen"
    M3E_CACHE="$CACHE_HOME/m3e-gnome"
    SRC_DIR="$M3E_CACHE/src"
    EXT_DEST="$DATA_HOME/gnome-shell/extensions"
    HOME_URL="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$HOME")"
    export DATA_HOME CONFIG_HOME CACHE_HOME
}

# Run a mutating command, or only print it with --dry-run.
run() {
    if ((DRY_RUN)); then
        printf '   [dry-run] %s\n' "$(printf '%q ' "$@")"
    else
        "$@"
    fi
}

have() { command -v "$1" >/dev/null 2>&1; }

# Temporary directories removed on exit. Only directories created by make_tmp are ever removed.
TMP_DIRS=()
# make_tmp stores the new directory in $REPLY (not on stdout: a command substitution would lose the bookkeeping).
make_tmp() {
    REPLY="$(mktemp -d "${TMPDIR:-/tmp}/m3e-gnome.XXXXXX")"
    TMP_DIRS+=("$REPLY")
}
cleanup_tmp() {
    local d
    for d in "${TMP_DIRS[@]}"; do
        [[ -n "$d" && "$d" == */m3e-gnome.* ]] && rm -rf -- "${d:?}"
    done
    TMP_DIRS=()
}

confirm() { # prompt -> 0 when the user agrees (always with --yes)
    ((ASSUME_YES)) && return 0
    [[ -t 0 ]] || return 1
    local reply
    read -r -p "$1 [y/N] " reply
    [[ "$reply" == [yY] || "$reply" == [yY][eE][sS] ]]
}

# Package-manager family from os-release ID / ID_LIKE: debian, fedora, arch, suse, or "unknown".
os_family() {
    local file="${M3E_OS_RELEASE:-/etc/os-release}" id='' like='' word
    [[ -r "$file" ]] || { echo unknown; return 0; }
    # shellcheck source=/dev/null
    id="$(. "$file" 2>/dev/null; printf '%s' "${ID:-}")"
    # shellcheck source=/dev/null
    like="$(. "$file" 2>/dev/null; printf '%s' "${ID_LIKE:-}")"
    for word in $id $like; do
        case "$word" in
            debian|ubuntu) echo debian; return 0 ;;
            fedora|rhel|centos) echo fedora; return 0 ;;
            arch) echo arch; return 0 ;;
            suse|opensuse|opensuse-leap|opensuse-tumbleweed|sles) echo suse; return 0 ;;
        esac
    done
    echo unknown
}

# Refuse any path that is not strictly inside $HOME (used before every recursive removal).
assert_inside_home() {
    local p="${1:?path required}"
    [[ "$p" == "$HOME"/* && "$p" != *'/../'* && "$p" != */.. && "$p" != "$HOME/" ]] ||
        die "refusing to touch a path outside \$HOME: $p"
}
