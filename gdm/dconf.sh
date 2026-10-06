# shellcheck shell=bash
# Greeter settings (icon theme, cursor, font, dark scheme) through a dconf database for the `gdm` profile, the way GDM
# documents it. Our database is added to the profile without replacing the distribution's. Requires common.sh.

DCONF_DB_NAME=m3e-gdm
PROFILE_LOGICAL=/etc/dconf/profile/gdm
DB_DIR_LOGICAL=/etc/dconf/db/m3e-gdm.d
DB_FILE_LOGICAL=/etc/dconf/db/m3e-gdm

conf_get() { sed -n "s/^$1=//p" "$2" | head -n1; }

# The profile we install: the base profile (the /etc one if there is one, else the distribution's under /usr/share, else
# the upstream default) with `system-db:m3e-gdm` right after the leading user-db lines. The base is kept in the state
# directory on the first run so that re-running regenerates the same thing.
profile_base() {
    local keep=$STATE/dconf-profile.base
    if [[ -f "$keep" ]]; then cat -- "$keep"
    elif [[ -f "$(rp "$PROFILE_LOGICAL")" ]] && ! m_has F "$PROFILE_LOGICAL"; then cat -- "$(rp "$PROFILE_LOGICAL")"
    elif [[ -f "$(rp /usr/share/dconf/profile/gdm)" ]]; then cat -- "$(rp /usr/share/dconf/profile/gdm)"
    else printf 'user-db:user\nsystem-db:gdm\nfile-db:/usr/share/gdm/greeter-dconf-defaults\n'; fi
}

profile_compose() { # base on stdin
    awk -v db="system-db:$DCONF_DB_NAME" '
        { lines[++n] = $0 }
        END {
            last = 0
            for (i = 1; i <= n; i++) { if (lines[i] ~ /^user-db:/) last = i; if (lines[i] == db) have = 1 }
            if (have) { for (i = 1; i <= n; i++) print lines[i]; exit }
            for (i = 1; i <= last; i++) print lines[i]
            print db
            for (i = last + 1; i <= n; i++) print lines[i]
        }'
}

dconf_apply() { # staged-data-dir
    local data=$1 icon cursor font w base
    icon=$(conf_get icon_theme "$data/greeter.conf"); cursor=$(conf_get cursor_theme "$data/greeter.conf")
    font=$(conf_get font_name "$data/greeter.conf")
    make_work; w=$REPLY
    base=$(profile_base)
    if ((! DRY_RUN)) && [[ ! -f "$STATE/dconf-profile.base" ]]; then
        printf '%s\n' "$base" >"$STATE/dconf-profile.base"; chmod 600 -- "$STATE/dconf-profile.base"
    fi
    printf '%s\n' "$base" | profile_compose >"$w/profile"
    cat >"$w/keyfile" <<EOT
# Managed by m3e-gnome (m3e-gdm). Edit the staged data instead: this file is rewritten.
[org/gnome/desktop/interface]
icon-theme='$icon'
cursor-theme='$cursor'
font-name='$font'
color-scheme='prefer-dark'
EOT
    claim_dest "$PROFILE_LOGICAL"
    put_atomic "$w/profile" "$PROFILE_LOGICAL" 644
    ensure_dir "$DB_DIR_LOGICAL"
    put_atomic "$w/keyfile" "$DB_DIR_LOGICAL/00-m3e-gdm" 644
    dconf_compile
}

dconf_compile() {
    # `dconf update` compiles every /etc/dconf/db/*.d; compiling only ours is the same operation for our database.
    m_has F "$DB_FILE_LOGICAL" || m_add F "$DB_FILE_LOGICAL"
    run dconf compile "$(rp "$DB_FILE_LOGICAL")" "$(rp "$DB_DIR_LOGICAL")"
}
