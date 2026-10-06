# shellcheck shell=bash
# The sub-commands of m3e-gdm. Requires every other lib file.

require_root() {
    ((DRY_RUN)) && return 0
    ((EUID == 0)) || [[ -n "$ROOT" ]] || die "this command changes the system and must run as root (use sudo)"
}

preflight() {
    need_tools glib-compile-resources gresource python3 install mktemp sha256sum dconf cmp awk sed grep find cp mv
    have gnome-shell || die "gnome-shell not found: this is not a GNOME system"
    local major
    major=$(shell_major)
    if [[ "$major" != "$M3E_GDM_TESTED_MAJOR" ]]; then
        ((FORCE)) || die "GNOME Shell $major found, this helper was verified with $M3E_GDM_TESTED_MAJOR only (use --force to try anyway)"
        warn "GNOME Shell $major is untested (verified: $M3E_GDM_TESTED_MAJOR); continuing because of --force"
    fi
    local u found=0
    for u in usr/lib/systemd/system lib/systemd/system etc/systemd/system; do
        [[ -e "$(rp "/$u/gdm.service")" || -e "$(rp "/$u/gdm3.service")" ]] && found=1
    done
    ((found)) || ((FORCE)) || die "GDM is not installed (no gdm.service): refusing (use --force to override)"
    [[ -f "$(rp "$GRES_LOGICAL")" || -f "$(rp "$GRES_LOGICAL.distrib")" ]] || die "the stock resource $GRES_LOGICAL is missing"
}

state_init() {
    local missing=() cur=$STATE_LOGICAL m
    ((DRY_RUN)) && return 0
    while [[ ! -d "$(rp "$cur")" ]]; do missing=("$cur" "${missing[@]}"); cur=$(dirname -- "$cur"); done
    for m in "${missing[@]}"; do safe_logical "$m"; mkdir -m 755 -- "$(rp "$m")"; done
    [[ -d "$STATE/backup" ]] || mkdir -m 700 -- "$STATE/backup"
    touch -- "$STATE/manifest"
    chmod 644 -- "$STATE/manifest"
    for m in "${missing[@]}"; do [[ "$m" == "$STATE_LOGICAL" ]] || m_has D "$m" || m_add D "$m"; done
}

register_helper() {
    if [[ "$HERE" == "$(rp "$HELPER_DIR_LOGICAL")" ]]; then
        m_has T "$HELPER_DIR_LOGICAL" || m_add T "$HELPER_DIR_LOGICAL"
        [[ -L "$(rp "$HELPER_LINK_LOGICAL")" ]] && { m_has F "$HELPER_LINK_LOGICAL" || m_add F "$HELPER_LINK_LOGICAL"; }
        # Parent directories the installer had to create (it lists them in a root-owned file of this directory).
        local d
        if [[ -f "$HERE/created-dirs" ]]; then
            while IFS= read -r d; do
                [[ -n "$d" ]] || continue
                safe_logical "$d"
                m_has D "$d" || m_add D "$d"
            done <"$HERE/created-dirs"
        fi
    fi
    return 0
}

stage_hash_ok() {
    [[ -f "$STATE/data.sha256" && -d "$STATE/data" ]] || return 1
    [[ "$(python3 -I -B "$HERE/ingest.py" hash "$STATE/data")" == "$(<"$STATE/data.sha256")" ]]
}

# Replace the staged data with a validated copy of $1 (swap by rename; the old copy stays until the new one is in place).
stage_ingest() {
    local src=$1
    if ((DRY_RUN)); then
        python3 -I -B "$HERE/ingest.py" check "$src" || die "the input data was refused"
        say "input data accepted (dry run: nothing staged)"
        return 0
    fi
    rm -rf -- "${STATE:?}/data.new" "${STATE:?}/data.old"
    python3 -I -B "$HERE/ingest.py" ingest "$src" "$STATE/data.new" || die "the input data was refused"
    [[ ! -d "$STATE/data" ]] || mv -- "$STATE/data" "$STATE/data.old"
    mv -- "$STATE/data.new" "$STATE/data"
    rm -rf -- "${STATE:?}/data.old"
    python3 -I -B "$HERE/ingest.py" hash "$STATE/data" | state_write data.sha256
}

cmd_apply() {
    local from=$1 forced=$2 data stock out stock_sha
    [[ -n "$from" && -d "$from" ]] || die "apply needs --from DIR (a directory prepared by the installer)"
    require_root
    take_lock
    preflight
    mech_detect "$forced"
    mech_preflight
    say "mechanism: $MECH"
    # Refuse bad input before anything exists on disk (the ingest below validates again what it actually copies).
    python3 -I -B "$HERE/ingest.py" check "$from" || die "the input data was refused"
    state_init
    register_helper
    stage_ingest "$from"
    if ((DRY_RUN)); then data=$from; else data=$STATE/data; fi
    stock=$(mech_stock)
    stock_sha=$(sha_of "$stock")
    make_work; out=$REPLY/built.gresource
    build_resource "$stock" "$data" "$out"
    say "resource built and verified from $stock"
    assets_apply "$data"
    dconf_apply "$data"
    hooks_apply
    printf '%s\n' "$MECH" | state_write mech
    record_pending "$(sha_of "$out")"
    mech_install "$out"
    if ((DRY_RUN)); then say "dry run: nothing was changed"; return 0; fi
    commit_identity "$stock_sha" "$(sha_of "$out")"
    rm -f -- "$STATE/disabled"
    say "installed. Reboot (or log out and restart GDM) to see the login screen; recovery: sudo m3e-gdm restore"
}

cmd_refresh() {
    [[ -f "$STATE/manifest" && -f "$STATE/mech" ]] || { say "not installed: nothing to refresh"; return 0; }
    require_root
    take_lock
    mech_detect "$(<"$STATE/mech")"
    local major stock out stock_sha data_ok=1
    major=$(shell_major)
    if [[ "$major" != "$M3E_GDM_TESTED_MAJOR" ]] && ((! FORCE)); then
        mech_activate_stock
        printf 'major %s\n' "$major" | state_write disabled
        warn "GNOME Shell $major is not the verified version ($M3E_GDM_TESTED_MAJOR): the stock login screen is back in service. 'sudo m3e-gdm refresh --force' rebuilds anyway."
        return 0
    fi
    stage_hash_ok || data_ok=0
    ((data_ok)) || die "the staged data does not match its recorded hash: refusing (re-run the installer with --gdm)"
    python3 -I -B "$HERE/ingest.py" check "$STATE/data" || die "the staged data no longer validates"
    stock=$(mech_stock)
    if [[ ! -f "$STATE/disabled" && -f "$STATE/stock.sha256" && "$(sha_of "$stock")" == "$(<"$STATE/stock.sha256")" &&
        -f "$STATE/built.sha256" && "$(mech_live_sha)" == "$(<"$STATE/built.sha256")" ]]; then
        say "up to date"
        return 0
    fi
    stock_sha=$(sha_of "$stock")
    make_work; out=$REPLY/built.gresource
    build_resource "$stock" "$STATE/data" "$out"
    record_pending "$(sha_of "$out")"
    mech_install "$out"
    commit_identity "$stock_sha" "$(sha_of "$out")"
    rm -f -- "$STATE/disabled"
    say "rebuilt from the current stock resource"
}

cmd_status() {
    [[ -f "$STATE/manifest" ]] || { echo "installed: no"; return 0; }
    mech_detect "$(<"$STATE/mech")"
    echo "installed: yes"
    echo "mechanism: $MECH"
    echo "disabled: $([[ -f "$STATE/disabled" ]] && echo yes || echo no)"
    echo "data-hash-ok: $(stage_hash_ok && echo yes || echo no)"
    echo "live-sha256: $(mech_live_sha)"
    echo "built-sha256: $(<"$STATE/built.sha256")"
}

remove_helper() {
    local d dirs=()
    if [[ "$HERE" == "$(rp "$HELPER_DIR_LOGICAL")" ]]; then
        # The parent directories the installer created are listed next to the code: they go with it, even when no apply
        # ever got as far as writing a manifest.
        if [[ -f "$HERE/created-dirs" ]]; then
            while IFS= read -r d; do [[ -n "$d" ]] && { safe_logical "$d"; dirs+=("$d"); }; done < <(tac -- "$HERE/created-dirs")
        fi
        rm_logical file "$HELPER_LINK_LOGICAL"
        rm_logical tree "$HELPER_DIR_LOGICAL"
        for d in "${dirs[@]}"; do ((DRY_RUN)) || rmdir -- "$(rp "$d")" 2>/dev/null || true; done
    else
        warn "this copy of the helper is not the installed one ($HERE): not removing it"
    fi
}

cmd_restore() {
    require_root
    take_lock
    if [[ ! -f "$STATE/manifest" ]]; then
        say "nothing to restore (no manifest)"
        ((REMOVE_HELPER)) && remove_helper
        return 0
    fi
    local recorded_mech=''
    if [[ -f "$STATE/mech" ]]; then recorded_mech=$(cat "$STATE/mech"); fi
    mech_detect "$recorded_mech"
    mech_remove
    local lines=() line kind a b c d e dirs=()
    mapfile -t lines < <(tac -- "$STATE/manifest")
    for line in "${lines[@]}"; do
        IFS=$'\t' read -r kind a b c d e <<<"$line"
        case "$kind" in
            F)
                case "$a" in "$GRES_LOGICAL"|"$GRES_LOGICAL.distrib"|"$HELPER_LINK_LOGICAL") continue ;; esac
                rm_logical file "$a" ;;
            T)
                [[ "$a" == "$HELPER_DIR_LOGICAL" ]] && continue
                rm_logical tree "$a" ;;
            B)
                safe_logical "$a"
                [[ "$b" =~ ^[0-9A-Za-z.]+$ ]] || die "corrupt manifest (backup name)"
                if ((DRY_RUN)); then printf '   [dry-run] restore %s from the backup\n' "$a"
                elif [[ -e "$STATE/backup/$b" ]]; then mv -- "$STATE/backup/$b" "$(rp "$a")"
                else warn "backup missing for $a"; fi ;;
            X)
                [[ "$a" == alt ]] && mech_restore_alt_mode "$b" "$c" "$d" "$e" ;;
            D) dirs+=("$a") ;;
            '') ;;
            *) die "corrupt manifest line: $line" ;;
        esac
    done
    if ((DRY_RUN)); then say "dry run: nothing was changed"; return 0; fi
    [[ "$STATE" == "$ROOT$STATE_LOGICAL" ]] || die "internal error: state path"
    rm -rf -- "${STATE:?}"
    ((REMOVE_HELPER)) && remove_helper
    # A directory we created that is no longer empty is in use by something else: keep it.
    for a in "${dirs[@]}"; do rmdir -- "$(rp "$a")" 2>/dev/null || true; done
    say "restored: the stock login screen resources are back"
    return 0
}
