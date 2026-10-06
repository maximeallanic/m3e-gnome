# shellcheck shell=bash
# System-wide greeter assets: icon and cursor themes, fonts (the greeter runs as the `gdm` user and cannot see the
# user's home), and the blurred background. Everything comes from the validated staging copy. Requires common.sh.

assets_apply() { # staged-data-dir
    local data=$1 kind d name dest
    for kind in icons fonts; do
        [[ -d "$data/assets/$kind" ]] || continue
        for d in "$data/assets/$kind"/*/; do
            [[ -d "$d" ]] || continue
            name=$(basename -- "$d")
            [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || die "unexpected theme name in the staged assets: $name"
            dest=/usr/local/share/$kind/$name
            safe_logical "$dest"
            claim_dest "$dest"
            if m_has T "$dest"; then rm_logical tree "$dest"; else m_add T "$dest"; fi
            ensure_dir "/usr/local/share/$kind"
            if ((DRY_RUN)); then printf '   [dry-run] copy %s -> %s\n' "$name" "$dest"; continue; fi
            cp -r --no-preserve=mode,ownership -- "$d" "$(rp "$dest")"
            find "$(rp "$dest")" -type d -exec chmod 755 {} +
            find "$(rp "$dest")" -type f -exec chmod 644 {} +
            # No fc-cache and no gtk-update-icon-cache here: they would parse staged font and icon bytes as root. The
            # greeter builds its font cache on demand and works without an icon cache (docs/gdm.md explains the cost).
        done
    done
    if [[ -f "$data/background.png" ]]; then
        put_atomic "$data/background.png" "$BG_LOGICAL" 644
    elif m_has F "$BG_LOGICAL"; then
        rm_logical file "$BG_LOGICAL"
    fi
    return 0
}
