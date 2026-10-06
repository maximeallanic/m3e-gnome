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
            if [[ "$kind" == icons ]] && have gtk-update-icon-cache; then gtk-update-icon-cache -q -f "$(rp "$dest")"; fi
            if [[ "$kind" == fonts ]] && have fc-cache; then fc-cache -f "$(rp "$dest")"; fi
        done
    done
    if [[ -f "$data/background.png" ]]; then
        put_atomic "$data/background.png" "$BG_LOGICAL" 644
    elif m_has F "$BG_LOGICAL"; then
        rm_logical file "$BG_LOGICAL"
    fi
    return 0
}
