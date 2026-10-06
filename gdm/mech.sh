# shellcheck shell=bash
# How the greeter's gnome-shell-theme.gresource is replaced, per distribution family. Requires common.sh, build.sh.
#
#   alternatives  Debian-family systems that register a gdm theme alternative (Ubuntu: gdm-theme.gresource): our file is
#                 added as a higher-priority candidate, the package-owned files are never touched, updates need no care.
#   divert        Debian-family without that alternative (Debian 13+/forky): dpkg-divert moves the stock file to
#                 <file>.distrib (future package updates write there), ours takes its place. Same technique as the
#                 original private script, but the swap is atomic: the file never disappears.
#   inplace       anything else (Fedora, Arch, openSUSE, unknown): ours replaces the stock file, the stock bytes are kept
#                 in the state directory. A package update overwrites ours; the refresh hook rebuilds it.
#
# Interface used by m3e-gdm: mech_detect, mech_stock (path of the CURRENT stock resource), mech_install BUILT,
# mech_activate_stock, mech_remove, mech_state (read-only description), mech_live_sha.

MECH=''
ALT_NAMES=(gdm-theme.gresource gdm3-theme.gresource)
ALT_PRIORITY=900
OURS_LOGICAL=$SHARE_LOGICAL/gdm-theme.gresource
DISTRIB_LOGICAL=$GRES_LOGICAL.distrib
STOCKCOPY_LOGICAL=$STATE_LOGICAL/stock/gnome-shell-theme.gresource
ALT_NAME=''
ALT_LINK=''

DPKG_OPTS=(); UA_OPTS=()
if [[ -n "$ROOT" ]]; then
    DPKG_OPTS=(--admindir "$ROOT/var/lib/dpkg" --instdir "$ROOT")
    UA_OPTS=(--altdir "$ROOT/etc/alternatives" --admindir "$ROOT/var/lib/dpkg/alternatives")
fi
divert_cmd() { dpkg-divert "${DPKG_OPTS[@]}" "$@"; }
ua_cmd() { update-alternatives "${UA_OPTS[@]}" "$@"; }

# Registered alternative name and link, or nothing.
alt_probe() {
    local n out
    have update-alternatives || return 1
    for n in "${ALT_NAMES[@]}"; do
        if out=$(ua_cmd --query "$n" 2>/dev/null); then
            ALT_NAME=$n
            ALT_LINK=$(sed -n 's/^Link: //p' <<<"$out" | head -n1)
            [[ -n "$ROOT" ]] && ALT_LINK=${ALT_LINK#"$ROOT"}
            [[ -n "$ALT_LINK" ]] && return 0
        fi
    done
    return 1
}

mech_detect() { # [forced]
    if [[ -n "${1:-}" ]]; then MECH=$1
    elif [[ -f "$STATE/mech" ]]; then MECH=$(<"$STATE/mech")
    elif alt_probe; then MECH=alternatives
    elif [[ "$(os_family)" == debian ]] && have dpkg-divert; then MECH=divert
    else MECH=inplace; fi
    case "$MECH" in
        alternatives) alt_probe || die "no gdm theme alternative is registered on this system" ;;
        divert) need_tools dpkg-divert ;;
        inplace) ;;
        *) die "unknown mechanism: $MECH" ;;
    esac
}

divert_owner() { divert_cmd --listpackage "$GRES_LOGICAL" 2>/dev/null || true; }

mech_preflight() {
    local owner
    case "$MECH" in
        divert)
            owner=$(divert_owner)
            if [[ -n "$owner" && "$owner" != m3e-gnome ]]; then
                die "$GRES_LOGICAL is already diverted by '$owner'. If that is the old private theme-gdm script, run its --restore first (sudo /usr/local/sbin/theme-gdm --restore); otherwise remove that diversion yourself."
            fi ;;
        alternatives) ;;
        inplace) ;;
    esac
}

# Highest-priority alternative candidate that is not ours.
alt_stock() {
    local out
    out=$(ua_cmd --query "$ALT_NAME") || die "cannot query $ALT_NAME"
    awk -v ours="$ROOT$OURS_LOGICAL" '
        /^Alternative: / { cand = substr($0, 14) }
        /^Priority: / { if (cand != ours && cand != "" && ($2 + 0 > best || best == "")) { best = $2 + 0; path = cand } cand = "" }
        END { if (path != "") print path }' <<<"$out"
}

inplace_live_is_ours() {
    local live f
    live=$(rp "$GRES_LOGICAL")
    [[ -f "$live" ]] || return 1
    live=$(sha_of "$live")
    for f in built.sha256 pending.sha256; do
        [[ -f "$STATE/$f" && "$live" == "$(<"$STATE/$f")" ]] && return 0
    done
    return 1
}

mech_stock() {
    local p
    case "$MECH" in
        alternatives) p=$(alt_stock); [[ -n "$p" ]] || die "$ALT_NAME has no stock candidate"; printf '%s' "$p" ;;
        divert)
            if [[ "$(divert_owner)" == m3e-gnome ]]; then rp "$DISTRIB_LOGICAL"; else rp "$GRES_LOGICAL"; fi ;;
        inplace)
            if [[ -f "$STATE/stock/gnome-shell-theme.gresource" ]] && inplace_live_is_ours; then
                printf '%s' "$STATE/stock/gnome-shell-theme.gresource"
            else
                rp "$GRES_LOGICAL"   # no copy yet, or a package replaced ours: the live file is the (new) stock
            fi ;;
    esac
}

mech_live_path() {
    case "$MECH" in
        alternatives) printf '%s' "$ROOT$OURS_LOGICAL" ;;
        *) rp "$GRES_LOGICAL" ;;
    esac
}
mech_live_sha() { sha_of "$(mech_live_path)"; }

# Make sure the stock copy we may need is safe, then put BUILT in place.
mech_install() { # built
    local built=$1 stock
    case "$MECH" in
        divert)
            if [[ "$(divert_owner)" != m3e-gnome ]]; then
                m_add X divert "$GRES_LOGICAL"
                if ((DRY_RUN)); then
                    printf '   [dry-run] dpkg-divert --no-rename --add --package m3e-gnome --divert %s %s\n   [dry-run] copy the stock file to %s\n' \
                        "$DISTRIB_LOGICAL" "$GRES_LOGICAL" "$DISTRIB_LOGICAL"
                else
                    divert_cmd --quiet --no-rename --add --package m3e-gnome --divert "$DISTRIB_LOGICAL" "$GRES_LOGICAL" || die "dpkg-divert --add failed"
                    if ! install -m 644 -- "$(rp "$GRES_LOGICAL")" "$(rp "$DISTRIB_LOGICAL").m3e-new" ||
                        ! mv -f -- "$(rp "$DISTRIB_LOGICAL").m3e-new" "$(rp "$DISTRIB_LOGICAL")"; then
                        divert_cmd --quiet --no-rename --remove --package m3e-gnome "$GRES_LOGICAL" || true
                        die "could not copy the stock resource aside; the diversion was rolled back"
                    fi
                fi
            fi
            put_atomic "$built" "$GRES_LOGICAL" 644 ;;
        inplace)
            if [[ ! -f "$STATE/stock/gnome-shell-theme.gresource" ]] || ! inplace_live_is_ours; then
                stock=$(rp "$GRES_LOGICAL")
                if grep -qaF -- "m3e-gnome gdm" <(gresource extract "$stock" "$GRES_PREFIX/gnome-shell-dark.css" 2>/dev/null); then
                    die "$GRES_LOGICAL already carries our marker but no stock copy exists: restore the stock resource first (docs/gdm.md, "Recovery from a TTY"), then retry"
                fi
                ensure_dir "$(dirname -- "$STOCKCOPY_LOGICAL")" 700
                m_has F "$STOCKCOPY_LOGICAL" || m_add F "$STOCKCOPY_LOGICAL"
                if ((DRY_RUN)); then printf '   [dry-run] keep a copy of the stock file in %s\n' "$STOCKCOPY_LOGICAL"
                else install -m 600 -- "$stock" "$STATE/stock/gnome-shell-theme.gresource"; fi
            fi
            put_atomic "$built" "$GRES_LOGICAL" 644 ;;
        alternatives)
            put_atomic "$built" "$OURS_LOGICAL" 644
            if ((DRY_RUN)); then
                printf '   [dry-run] update-alternatives --install %s %s %s %s\n' "$ALT_LINK" "$ALT_NAME" "$OURS_LOGICAL" "$ALT_PRIORITY"
            else
                if ! grep -q "^X	alt	$ALT_NAME	" "$STATE/manifest" 2>/dev/null; then
                    local mode path
                    mode=$(ua_cmd --query "$ALT_NAME" | sed -n 's/^Status: //p' | head -n1)
                    path=$(ua_cmd --query "$ALT_NAME" | sed -n 's/^Value: //p' | head -n1)
                    m_add X alt "$ALT_NAME" "$ALT_LINK" "$mode" "${path#"$ROOT"}"
                fi
                ua_cmd --quiet --install "$ROOT$ALT_LINK" "$ALT_NAME" "$ROOT$OURS_LOGICAL" "$ALT_PRIORITY" || die "update-alternatives --install failed"
                ua_cmd --quiet --set "$ALT_NAME" "$ROOT$OURS_LOGICAL" || die "update-alternatives --set failed"
            fi ;;
    esac
}

# Put the stock resource back in service without forgetting our state (used when GNOME Shell changed major version).
mech_activate_stock() {
    case "$MECH" in
        divert) put_atomic "$(rp "$DISTRIB_LOGICAL")" "$GRES_LOGICAL" 644 ;;
        inplace) if inplace_live_is_ours; then put_atomic "$STATE/stock/gnome-shell-theme.gresource" "$GRES_LOGICAL" 644; fi ;;
        alternatives)
            ((DRY_RUN)) || ua_cmd --quiet --remove "$ALT_NAME" "$ROOT$OURS_LOGICAL" ;;
    esac
}

# Undo the mechanism exactly: the stock resource is back, diversion / alternative / copy gone.
mech_remove() {
    case "$MECH" in
        divert)
            if [[ "$(divert_owner)" == m3e-gnome ]]; then
                if [[ -f "$(rp "$DISTRIB_LOGICAL")" ]]; then
                    put_atomic "$(rp "$DISTRIB_LOGICAL")" "$GRES_LOGICAL" 644
                else
                    warn "$DISTRIB_LOGICAL is missing, so the stock resource cannot be put back from it: the diversion is removed; get the stock file with: sudo apt reinstall gnome-shell-common"
                fi
                run divert_cmd --quiet --no-rename --remove --package m3e-gnome "$GRES_LOGICAL"
                rm_logical file "$DISTRIB_LOGICAL"
            fi ;;
        inplace)
            if [[ -f "$STATE/stock/gnome-shell-theme.gresource" ]] && inplace_live_is_ours; then
                put_atomic "$STATE/stock/gnome-shell-theme.gresource" "$GRES_LOGICAL" 644
            else
                say "the live resource is not ours any more (a package replaced it): left alone"
            fi ;;
        alternatives)
            alt_probe || true
            if [[ -n "$ALT_NAME" ]]; then run ua_cmd --quiet --remove "$ALT_NAME" "$ROOT$OURS_LOGICAL"; fi ;;
    esac
}

# Restore the previous manual alternative selection, if it was manual (called after mech_remove by restore).
mech_restore_alt_mode() { # name link mode path
    if [[ "$3" == manual && -n "$4" && -e "$ROOT$4" ]]; then run ua_cmd --quiet --set "$1" "$ROOT$4"; fi
}
