# shellcheck shell=bash
# Fixtures for the GDM tests: a fake system root (the helper is redirected into it with M3E_GDM_TEST=1 and M3E_GDM_ROOT,
# which it refuses when running as root), stock resources, and input data directories. Needs lib.sh.
# Real dpkg-divert, update-alternatives, glib-compile-resources and dconf are used inside the fake root.

GDM_SRC="$REPO/gdm"

gdm_setup() {
    T_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/m3e-test.XXXXXX")"
    export T_ROOT NO_COLOR=1 TMPDIR="$T_ROOT/tmp"
    mkdir -p "$TMPDIR" "$T_ROOT/bin"
    ln -s "$TESTS_DIR/shims/gnome-shell" "$T_ROOT/bin/gnome-shell"
    ln -s "$TESTS_DIR/shims/fc-cache" "$T_ROOT/bin/fc-cache"
    ln -s "$TESTS_DIR/shims/gtk-update-icon-cache" "$T_ROOT/bin/gtk-update-icon-cache"
    export PATH="$T_ROOT/bin:/usr/bin:/bin"
}

# Stock resource with the layout of GNOME Shell 50 (two stylesheets, an asset, an unrelated stylesheet).
gdm_make_stock() { # out-file tag
    local d="$T_ROOT/stock-src.$2"
    mkdir -p "$d"
    printf '/* stock light %s */\nstage { color: #111; }\n' "$2" >"$d/gnome-shell-light.css"
    printf '/* stock dark %s */\nstage { color: #eee; }' "$2" >"$d/gnome-shell-dark.css"
    printf '/* hc */\n' >"$d/gnome-shell-high-contrast.css"
    mkdir -p "$d/assets"
    printf '<svg xmlns="http://www.w3.org/2000/svg"/>\n' >"$d/assets/toggle-on.svg"
    {
        echo '<?xml version="1.0" encoding="UTF-8"?><gresources><gresource prefix="/org/gnome/shell/theme">'
        (cd "$d" && find . -type f | sed 's|^\./||' | LC_ALL=C sort | sed 's|.*|<file>&</file>|')
        echo '</gresource></gresources>'
    } >"$d/x.xml"
    glib-compile-resources --sourcedir="$d" --target="$1" "$d/x.xml"
    chmod 644 "$1"
}

# gdm_make_root DIR family(debian|ubuntu|arch|fedora)
gdm_make_root() {
    local r="$1" family="$2"
    mkdir -p "$r"/usr/share/gnome-shell "$r"/etc "$r"/usr/lib/systemd/system "$r"/usr/share/dconf/profile "$r"/usr/local \
        "$r"/var/lib/dpkg/updates "$r"/var/lib/dpkg/alternatives "$r"/etc/alternatives "$r"/etc/dconf/db
    : >"$r/usr/lib/systemd/system/gdm.service"
    : >"$r/var/lib/dpkg/status"; : >"$r/var/lib/dpkg/diversions"; chmod 644 "$r/var/lib/dpkg/status" "$r/var/lib/dpkg/diversions"
    printf 'user-db:user\nfile-db:/var/lib/gdm3/greeter-dconf-defaults\n' >"$r/usr/share/dconf/profile/gdm"
    case "$family" in
        debian) printf 'ID=debian\n' >"$r/etc/os-release"; mkdir -p "$r/etc/apt/apt.conf.d"
            gdm_make_stock "$r/usr/share/gnome-shell/gnome-shell-theme.gresource" v1 ;;
        ubuntu)
            printf 'ID=ubuntu\nID_LIKE=debian\n' >"$r/etc/os-release"; mkdir -p "$r/etc/apt/apt.conf.d" "$r/usr/share/gnome-shell/theme/Yaru"
            gdm_make_stock "$r/usr/share/gnome-shell/gnome-shell-theme.gresource" generic
            gdm_make_stock "$r/usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource" yaru
            update-alternatives --altdir "$r/etc/alternatives" --admindir "$r/var/lib/dpkg/alternatives" --quiet --install \
                "$r/usr/share/gnome-shell/gdm-theme.gresource" gdm-theme.gresource "$r/usr/share/gnome-shell/gnome-shell-theme.gresource" 10
            update-alternatives --altdir "$r/etc/alternatives" --admindir "$r/var/lib/dpkg/alternatives" --quiet --install \
                "$r/usr/share/gnome-shell/gdm-theme.gresource" gdm-theme.gresource "$r/usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource" 15 ;;
        arch) printf 'ID=arch\n' >"$r/etc/os-release"; mkdir -p "$r/etc/pacman.d/hooks"
            gdm_make_stock "$r/usr/share/gnome-shell/gnome-shell-theme.gresource" v1 ;;
        fedora) printf 'ID=fedora\n' >"$r/etc/os-release"; mkdir -p "$r/etc/dnf/plugins/post-transaction-actions.d" "$r/etc/dnf/libdnf5-plugins/actions.d"
            gdm_make_stock "$r/usr/share/gnome-shell/gnome-shell-theme.gresource" v1 ;;
    esac
}

# A PNG of the given size written with the standard library (rows of one colour).
gdm_make_png() { # out w h
    python3 - "$@" <<'PY'
import struct, sys, zlib
out, w, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
raw = b"".join(b"\x00" + bytes([0x40, 0x60, 0x90]) * w for _ in range(min(h, 64)))
def chunk(t, d):
    c = struct.pack(">I", len(d)) + t + d
    return c + struct.pack(">I", zlib.crc32(t + d))
open(out, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                      + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
PY
}

# A valid input directory (what the user-side installer produces).
gdm_make_data() { # dir
    local d="$1"
    mkdir -p "$d/assets/icons/Material-Symbols/symbolic/actions" "$d/assets/icons/Googlebook/cursors" \
        "$d/assets/fonts/GoogleSansFlex"
    cat >"$d/theme.css" <<'EOT'
/* M3E fixture sheet */
#lockDialogGroup { background-color: #101418; }
.login-dialog { color: #e0e2e8; background-image: url("resource:///org/gnome/shell/theme/calendar-today-light.svg"); }
EOT
    printf 'icon_theme=Material-Symbols\ncursor_theme=Googlebook\nfont_name=Google Sans Flex 10.5\nseed=image\n' >"$d/greeter.conf"
    gdm_make_png "$d/background.png" 64 36
    printf '[Icon Theme]\nName=Material-Symbols\nInherits=Adwaita,hicolor\n' >"$d/assets/icons/Material-Symbols/index.theme"
    printf '<svg xmlns="http://www.w3.org/2000/svg"/>\n' >"$d/assets/icons/Material-Symbols/symbolic/actions/go-next-symbolic.svg"
    printf 'Xcur\0\0\0\0fixture' >"$d/assets/icons/Googlebook/cursors/left_ptr"
    printf '[Icon Theme]\nName=Googlebook\n' >"$d/assets/icons/Googlebook/index.theme"
    printf '\0\1\0\0fixture-font' >"$d/assets/fonts/GoogleSansFlex/GoogleSansFlex[GRAD,ROND].ttf"
    printf 'SIL OFL fixture\n' >"$d/assets/fonts/GoogleSansFlex/OFL.txt"
}

# Install the helper into the fake root exactly like the user-side installer does (sudo and chown skipped by the seam).
gdm_install_helper_into() { # root
    (
        # shellcheck disable=SC2030
        export M3E_GDM_TEST=1 M3E_GDM_ROOT="$1"
        # shellcheck source=lib/common.sh
        source "$REPO/lib/common.sh"
        # shellcheck source=lib/gdm.sh
        source "$REPO/lib/gdm.sh"
        REPO_ROOT="$REPO"
        gdm_install_helper
    )
}

# Run the installed helper against the fake root.
GR=''
gdm_run() { M3E_GDM_TEST=1 M3E_GDM_ROOT="$GR" "$GR/usr/local/libexec/m3e-gnome/gdm/m3e-gdm" "$@"; }

gdm_snapshot() { python3 "$TESTS_DIR/snapshot.py" "$1"; }

# The read-only verify section against the fake root; prints its lines, exit 0 when nothing failed.
gdm_verify() {
    (
        # shellcheck disable=SC2031
        export M3E_GDM_TEST=1 M3E_GDM_ROOT="$GR"
        # shellcheck source=lib/common.sh
        source "$REPO/lib/common.sh"
        for f in verify_checks gdm gdm_verify; do
            # shellcheck source=/dev/null
            source "$REPO/lib/$f.sh"
        done
        REPO_ROOT="$REPO"
        check_gdm
        ((V_FAIL == 0))
    )
}
