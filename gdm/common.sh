# shellcheck shell=bash
# Shared code of the root helper: environment hardening, test-root prefix, logging, atomic writes, manifest.
# Sourced by m3e-gdm after it has verified that this directory is trusted. Never executed. English messages only; tool
# output is always parsed under LC_ALL=C.

M3E_GDM_TESTED_MAJOR=50
GRES_LOGICAL=/usr/share/gnome-shell/gnome-shell-theme.gresource
GRES_PREFIX=/org/gnome/shell/theme
HELPER_DIR_LOGICAL=/usr/local/libexec/m3e-gnome/gdm
HELPER_LINK_LOGICAL=/usr/local/sbin/m3e-gdm
SHARE_LOGICAL=/usr/local/share/m3e-gnome/gdm
STATE_LOGICAL=/var/lib/m3e-gnome/gdm
BG_LOGICAL=$SHARE_LOGICAL/background.png
MARKER='/* m3e-gnome gdm */'
declare -A DRY_SEEN=()
DRY_RUN=0
FORCE=0
QUIET=0
ROOT=''

say() { ((QUIET)) || printf 'm3e-gdm: %s\n' "$*"; }
warn() { printf 'm3e-gdm: warning: %s\n' "$*" >&2; }
die() { printf 'm3e-gdm: error: %s\n' "$*" >&2; exit 1; }

# The environment of every program root spawns: PATH and the C locale, nothing else. Library, module, schema and
# configuration search paths of glib, gdk-pixbuf, fontconfig, python, dpkg, dconf ... all come from the caller otherwise.
sanitize_env() {
    local v f
    for v in $(compgen -e); do
        case "$v" in PATH|LC_ALL|LANGUAGE|PWD|OLDPWD|SHLVL|_|UID|EUID|PPID|BASHOPTS|SHELLOPTS) ;; *) unset -v "$v" ;; esac
    done
    for f in $(declare -Fx | awk '{print $3}'); do unset -f "$f"; done
    export PATH=/usr/sbin:/usr/bin:/sbin:/bin
    export LC_ALL=C LANGUAGE=C
}

# Environment. As root nothing from the caller's environment is trusted and the test hooks are refused outright;
# the ONLY way to redirect the helper is M3E_GDM_ROOT together with M3E_GDM_TEST=1, and only when not root.
harden_env() {
    umask 022
    if ((EUID == 0)); then
        if [[ -n "${M3E_GDM_TEST:-}" || -n "${M3E_GDM_ROOT:-}" ]]; then
            printf 'm3e-gdm: error: M3E_GDM_TEST / M3E_GDM_ROOT are test hooks and are refused when running as root\n' >&2
            exit 1
        fi
        sanitize_env
    else
        export LC_ALL=C LANGUAGE=C
        if [[ -n "${M3E_GDM_ROOT:-}" ]]; then
            [[ "${M3E_GDM_TEST:-}" == 1 ]] || die "M3E_GDM_ROOT needs M3E_GDM_TEST=1"
            [[ "$M3E_GDM_ROOT" == /* && "$M3E_GDM_ROOT" != / && -d "$M3E_GDM_ROOT" ]] ||
                die "M3E_GDM_ROOT must be an existing absolute directory other than /"
            ROOT="${M3E_GDM_ROOT%/}"
        fi
    fi
    STATE=$ROOT$STATE_LOGICAL
}

# One helper run at a time (apply, refresh and restore rewrite the same state). The lock lives in /run, which only root
# can write: a lock file in a sticky world-writable directory could be a link planted by a user.
LOCKFD=''
take_lock() {
    ((DRY_RUN)) && return 0
    local wait=60 file
    [[ -z "$ROOT" ]] || wait=${M3E_GDM_LOCK_WAIT:-60}   # test hook, only reachable in test mode
    file=$ROOT/run/m3e-gdm.lock
    [[ -d "$ROOT/run" ]] || die "/run does not exist"
    exec {LOCKFD}>"$file"
    flock -w "$wait" "$LOCKFD" || die "another m3e-gdm run is in progress (lock $file)"
}

# state_write NAME : atomically replace $STATE/NAME with stdin (0644).
state_write() {
    ((DRY_RUN)) && return 0
    local tmp="$STATE/.$1.m3e-new.$$"
    cat >"$tmp"
    chmod 644 -- "$tmp"
    mv -f -- "$tmp" "$STATE/$1"
}

# Path under the (test) root.
rp() { printf '%s%s' "$ROOT" "$1"; }

# Only paths in these places are ever written or removed.
safe_logical() {
    local p=$1
    [[ "$p" == /* && "$p" != *..* && "$p" != *$'\n'* && "$p" != *$'\t'* ]] || die "refusing unsafe path: $p"
    case "$p" in
        /usr/local/share/m3e-gnome/*|/usr/local/share/icons/?*|/usr/local/share/fonts/?*|/usr/local/libexec/m3e-gnome/*|\
        /usr/local/sbin/m3e-gdm|/usr/share/gnome-shell/gnome-shell-theme.gresource*|/etc/dconf/db/m3e-gdm*|\
        /etc/dconf/profile/gdm|/etc/apt/apt.conf.d/99m3e-gdm|/etc/pacman.d/hooks/m3e-gdm.hook|\
        /etc/dnf/plugins/post-transaction-actions.d/m3e-gdm.action|/etc/dnf/libdnf5-plugins/actions.d/m3e-gdm.actions|\
        /var/lib/m3e-gnome/gdm|/var/lib/m3e-gnome/gdm/*) ;;
        /usr/local|/usr/local/share|/usr/local/share/m3e-gnome|/usr/local/libexec/m3e-gnome|/usr/local/share/icons|/usr/local/share/fonts|/usr/local/libexec|/usr/local/sbin|\
        /var/lib|/var/lib/m3e-gnome|/etc/dconf|/etc/dconf/db|/etc/dconf/profile|/etc/apt/apt.conf.d|/etc/pacman.d|\
        /etc/pacman.d/hooks|/etc/dnf|/etc/dnf/plugins|/etc/dnf/plugins/post-transaction-actions.d|\
        /etc/dnf/libdnf5-plugins|/etc/dnf/libdnf5-plugins/actions.d) ;;
        *) die "refusing a path outside the helper's allow-list: $p" ;;
    esac
}

run() {
    if ((DRY_RUN)); then printf '   [dry-run] %s\n' "$(printf '%q ' "$@")"; else "$@"; fi
}

have() { command -v "$1" >/dev/null 2>&1; }
need_tools() {
    local t missing=()
    for t in "$@"; do have "$t" || missing+=("$t"); done
    ((${#missing[@]} == 0)) || die "missing tools: ${missing[*]}"
}

sha_of() { sha256sum -- "$1" | cut -d' ' -f1; }

# --- temp directories, removed on exit (only ones created here) ------------------------------------------------------
ORPHANS=()   # temporary names next to a destination, removed on exit if the rename never happened
TMP_MADE=()
make_work() {
    local base=${TMPDIR:-/tmp}
    REPLY=$(mktemp -d "$base/m3e-gdm.XXXXXX")
    TMP_MADE+=("$REPLY")
}
# shellcheck disable=SC2317,SC2329  # invoked through the EXIT trap
cleanup_work() {
    local d
    for d in "${TMP_MADE[@]}"; do
        if [[ -n "$d" && "$d" == */m3e-gdm.?????? ]]; then rm -rf -- "${d:?}"; fi
    done
    TMP_MADE=()
    for d in "${ORPHANS[@]}"; do
        if [[ "$d" == *.m3e-new.* && -f "$d" ]]; then rm -f -- "${d:?}"; fi
    done
    return 0
}

# --- manifest: tab-separated, appended BEFORE the change it describes -------------------------------------------------
#   F path          file we created or replaced     T path   tree we own     D path   directory we created (if empty)
#   B path backup   original moved to backup/<name>  X kind args...  special undo (divert, alternative, helper)
m_add() {
    ((DRY_RUN)) && return 0
    local IFS=$'\t'
    printf '%s\n' "$*" >>"$STATE/manifest"
}
m_has() { # kind path
    [[ -f "$STATE/manifest" ]] && grep -qxF -- "$1"$'\t'"$2" "$STATE/manifest"
}

ensure_dir() { # logical-dir mode ; records the directories it creates
    local d=$1 mode=${2:-755} missing=() cur
    cur=$d
    while [[ ! -d "$(rp "$cur")" ]]; do missing=("$cur" "${missing[@]}"); cur=$(dirname -- "$cur"); done
    local m
    for m in "${missing[@]}"; do
        safe_logical "$m"
        if ((DRY_RUN)); then
            [[ -n "${DRY_SEEN[$m]:-}" ]] || printf '   [dry-run] mkdir %s\n' "$m"
            DRY_SEEN[$m]=1
            continue
        fi
        m_add D "$m"
        mkdir -m "$mode" -- "$(rp "$m")"
    done
}

# Atomic replace: write next to the destination, then rename. Parent directories are created (and recorded).
put_atomic() { # src logical-dest mode
    local src=$1 dest=$2 mode=$3 tmp
    safe_logical "$dest"
    ensure_dir "$(dirname -- "$dest")"
    if ((DRY_RUN)); then printf '   [dry-run] install %s (mode %s)\n' "$dest" "$mode"; return 0; fi
    m_has F "$dest" || m_add F "$dest"
    tmp="$(rp "$dest").m3e-new.$$"
    ORPHANS+=("$tmp")
    install -m "$mode" -- "$src" "$tmp"
    mv -f -- "$tmp" "$(rp "$dest")"
}

# Remove a recorded path (guarded by safe_logical).
rm_logical() { # file|tree path
    local kind=$1 p=$2
    safe_logical "$p"
    [[ -e "$(rp "$p")" || -L "$(rp "$p")" ]] || return 0
    if ((DRY_RUN)); then printf '   [dry-run] remove %s\n' "$p"; return 0; fi
    if [[ "$kind" == tree ]]; then rm -rf -- "$ROOT${p:?}"; else rm -f -- "$ROOT${p:?}"; fi
}

# Move an existing path we do not own into the backup directory, recorded so restore puts it back.
claim_dest() { # logical-path
    local p=$1 n
    safe_logical "$p"
    [[ -e "$(rp "$p")" || -L "$(rp "$p")" ]] || return 0
    if m_has F "$p" || m_has T "$p"; then return 0; fi
    if ((DRY_RUN)); then printf '   [dry-run] back up existing %s\n' "$p"; return 0; fi
    n=$(date +%Y%m%d%H%M%S).$$.$RANDOM
    [[ -d "$STATE/backup" ]] || mkdir -m 700 -- "$STATE/backup"
    m_add B "$p" "$n"
    mv -- "$(rp "$p")" "$STATE/backup/$n"
}

os_family() {
    local f id like w
    f=$(rp /etc/os-release)
    [[ -r "$f" ]] || { echo unknown; return 0; }
    id=$(sed -n 's/^ID=//p' "$f" | head -n1 | tr -d '"'"'")
    like=$(sed -n 's/^ID_LIKE=//p' "$f" | head -n1 | tr -d '"'"'")
    for w in $id $like; do
        case "$w" in
            debian|ubuntu) echo debian; return 0 ;;
            fedora|rhel|centos) echo fedora; return 0 ;;
            arch) echo arch; return 0 ;;
            suse|opensuse|opensuse-leap|opensuse-tumbleweed|sles) echo suse; return 0 ;;
        esac
    done
    echo unknown
}

shell_major() {
    local v
    v=$(gnome-shell --version 2>/dev/null | sed -n 's/^GNOME Shell \([0-9][0-9]*\).*/\1/p' | head -n1)
    [[ -n "$v" ]] || die "cannot read the GNOME Shell version (gnome-shell --version)"
    printf '%s' "$v"
}
