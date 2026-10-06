# shellcheck shell=bash
# GNOME settings (gsettings/dconf). Every key is backed up (original dconf value) before it is first changed, so
# restore.sh and uninstall can put it back. Requires common.sh and backup.sh.

# dconf path of a schema key; a relocatable schema is given as "schema:/path/".
dconf_path() { # schema key
    local schema="$1" key="$2"
    if [[ "$schema" == *:* ]]; then
        printf '%s%s\n' "${schema#*:}" "$key"
    else
        printf '/%s/%s\n' "${schema//./\/}" "$key"
    fi
}

gs_schema_exists() { # schema (relocatable form accepted)
    local base="${1%%:*}" all
    # Captured first: `... | grep -q` would kill the producer early and fail under pipefail.
    all="$(gsettings list-schemas; gsettings list-relocatable-schemas)"
    [[ $'\n'"$all"$'\n' == *$'\n'"$base"$'\n'* ]]
}

# gs_set SCHEMA KEY GVARIANT: back up, then set. A failure to set stops the install.
gs_set() {
    local schema="$1" key="$2" value="$3"
    if ((DRY_RUN)); then msg_info "[dry-run] gsettings set $schema $key $value"; return 0; fi
    backup_dconf "$(dconf_path "$schema" "$key")"
    gsettings set "$schema" "$key" "$value" || die "gsettings set $schema $key failed"
}

# Same, for a schema that may not be installed (Dash to Dock, Ptyxis, ...): skipped with a note.
gs_set_if_schema() {
    if gs_schema_exists "$1"; then
        gs_set "$@"
    else
        msg_info "schema $1 not installed: $2 left alone"
    fi
}

gs_get() { gsettings get "$1" "$2" | tr -d "'"; } # strings only

# Back up now the keys that matugen hooks or material-sync will change later.
backup_dynamic_keys() {
    local k
    ((DRY_RUN)) && return 0
    for k in org.gnome.desktop.interface:accent-color org.gnome.shell.extensions.user-theme:name \
        org.gnome.desktop.interface:gtk-theme; do
        backup_dconf "$(dconf_path "${k%%:*}" "${k#*:}")"
    done
}

session_check() { # a GNOME session with a reachable settings backend
    have gnome-shell || die "gnome-shell not found: this theme is for GNOME"
    case ":${XDG_CURRENT_DESKTOP:-}:" in
        *:GNOME:*|*:gnome:*) ;;   # also matches "ubuntu:GNOME"
        *) die "not a GNOME session (XDG_CURRENT_DESKTOP='${XDG_CURRENT_DESKTOP:-}'). Run from your GNOME session, or pass --no-session-check" ;;
    esac
    [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" || -S "${XDG_RUNTIME_DIR:-/nonexistent}/bus" ]] ||
        die "no D-Bus session bus: GNOME settings would not be written. Run this inside your graphical session"
    gsettings get org.gnome.desktop.interface gtk-theme >/dev/null 2>&1 ||
        die "cannot read GNOME settings (gsettings failed): run this inside your graphical session"
    local ver major
    ver="$(gnome-shell --version 2>/dev/null | sed -n 's/^GNOME Shell \([0-9][0-9]*\).*/\1/p')"
    major="${ver:-?}"
    if [[ "$major" != "$TARGET_GNOME" ]]; then
        msg_warn "GNOME Shell $major detected; this theme and its extensions target GNOME $TARGET_GNOME (validated on 50.5): continuing"
    else
        msg_info "GNOME Shell $major"
    fi
}
