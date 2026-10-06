# shellcheck shell=bash
# Test helpers: a throw-away HOME, fake GNOME tools on PATH, git/file fixtures for every pinned source.
# Nothing here touches the real home directory or session: HOME is a temporary directory, gsettings/dconf/
# gnome-extensions/systemctl are shims, GSETTINGS_BACKEND=memory and a bogus bus are a second safety net.

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$TESTS_DIR")"
FAILS=0

pass() { printf '  ok    %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; FAILS=$((FAILS + 1)); }
check() { # description command...
    local d="$1"; shift
    if "$@" >/dev/null 2>&1; then pass "$d"; else fail "$d"; fi
}
check_not() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then fail "$d"; else pass "$d"; fi; }

# Tools looked up in the caller's PATH and exposed to the sandbox PATH when they live outside /usr/bin and /bin.
SANDBOX_TOOLS=(git rsync curl python3 node npm npx ffmpeg ffprobe rsvg-convert meson ninja sha256sum sort tar gzip
    install cmp awk sed xargs mktemp readlink env bash flock)

t_setup() {
    T_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/m3e-test.XXXXXX")"
    export T_ROOT
    export HOME="$T_ROOT/hôme with space" TMPDIR="$T_ROOT/tmp" M3E_FAKE_DIR="$T_ROOT/fake"
    mkdir -p "$HOME" "$TMPDIR" "$M3E_FAKE_DIR" "$T_ROOT/realbin"
    unset XDG_DATA_HOME XDG_CONFIG_HOME XDG_CACHE_HOME XDG_STATE_HOME
    export XDG_CURRENT_DESKTOP=GNOME
    export GSETTINGS_BACKEND=memory DBUS_SESSION_BUS_ADDRESS="unix:path=$T_ROOT/no-bus" DCONF_PROFILE="$T_ROOT/no-profile"
    export NO_COLOR=1
    # The GDM step uses sudo on a real system. Every sandboxed run is pointed at an empty fake system root through the
    # (user-level) test seam, so that no test can ever reach the real /usr, /etc or /var, or call sudo.
    mkdir -p "$T_ROOT/gdm-void-root"
    export M3E_GDM_TEST=1 M3E_GDM_ROOT="$T_ROOT/gdm-void-root"
    local t p
    for t in "${SANDBOX_TOOLS[@]}"; do
        p="$(command -v "$t" 2>/dev/null || true)"
        [[ -n "$p" ]] || continue
        case "$p" in /usr/bin/*|/bin/*) ;; *) ln -sf "$p" "$T_ROOT/realbin/$t" ;; esac
    done
    if [[ -z "${M3E_TEST_NO_MATUGEN:-}" ]]; then
        p="$(command -v matugen 2>/dev/null || true)"
        [[ -z "$p" ]] || ln -sf "$p" "$T_ROOT/realbin/matugen"
    fi
    ORIG_PATH="$PATH"
    export PATH="$TESTS_DIR/shims:$T_ROOT/realbin:/usr/bin:/bin"
    printf '%s\n' org.gnome.desktop.interface org.gnome.desktop.wm.preferences org.gnome.desktop.sound \
        org.gnome.shell org.gnome.shell.extensions.user-theme org.gnome.shell.extensions.dash-to-dock \
        org.gnome.Ptyxis org.gnome.Ptyxis.Profile >"$M3E_FAKE_DIR/schemas.txt"
    # A real session never has these tools resolving outside the shim directory.
    [[ "$(command -v gsettings)" == "$TESTS_DIR/shims/gsettings" ]] || { echo "sandbox PATH leak: gsettings" >&2; exit 2; }
    [[ "$(command -v dconf)" == "$TESTS_DIR/shims/dconf" ]] || { echo "sandbox PATH leak: dconf" >&2; exit 2; }
    case "$HOME" in "$TMPDIR"/*|/tmp/*|/var/tmp/*) ;; *) echo "HOME is not temporary: $HOME" >&2; exit 2 ;; esac
}

t_teardown() {
    [[ -z "${M3E_TEST_KEEP:-}" ]] || { echo "kept: $T_ROOT"; return 0; }
    [[ -n "${T_ROOT:-}" && "$T_ROOT" == */m3e-test.* ]] && rm -rf -- "${T_ROOT:?}"
}

snapshot() { python3 "$TESTS_DIR/snapshot.py" "$1"; }

fake_get() { # dconf-path -> stored value
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], "<unset>"))' \
        "$M3E_FAKE_DIR/dconf.json" "$1" 2>/dev/null || echo "<unset>"
}
fake_set() { # dconf-path value (pre-install state of the fake session)
    python3 - "$M3E_FAKE_DIR/dconf.json" "$1" "$2" <<'PY'
import json, os, sys
p = sys.argv[1]
d = json.load(open(p)) if os.path.exists(p) else {}
d[sys.argv[2]] = sys.argv[3]
json.dump(d, open(p, "w"))
PY
}

# A tiny git repository whose HEAD commit can be fetched by its sha (as the pins do).
make_git_fixture() { # dir  (files already in dir)
    git -C "$1" init -q
    git -C "$1" config user.email t@example.invalid
    git -C "$1" config user.name test
    git -C "$1" config uploadpack.allowAnySHA1InWant true
    git -C "$1" add -A
    git -C "$1" commit -q -m fixture
}
