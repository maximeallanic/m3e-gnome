# shellcheck shell=bash
# Refresh hooks: after a package transaction that may have replaced the stock gnome-shell resource, the package manager
# runs `m3e-gdm refresh` as root. The hook files are static text; they contain no path from the user's home.
# Requires common.sh. Status per family is in docs/gdm.md (Debian/Ubuntu verified here; the rest untested).

HOOK_CMD=/usr/local/sbin/m3e-gdm

hook_apt() {
    put_text /etc/apt/apt.conf.d/99m3e-gdm 644 <<EOT
// m3e-gnome: rebuild the GDM login-screen resource after a package update (see docs/gdm.md).
DPkg::Post-Invoke { "if [ -x $HOOK_CMD ]; then $HOOK_CMD refresh --quiet || echo 'm3e-gdm: refresh failed, run: sudo m3e-gdm refresh' >&2; fi"; };
EOT
}

hook_pacman() {
    put_text /etc/pacman.d/hooks/m3e-gdm.hook 644 <<EOT
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = gnome-shell

[Action]
Description = Rebuilding the m3e-gnome GDM login-screen resource
When = PostTransaction
Exec = $HOOK_CMD refresh --quiet
EOT
}

hook_dnf() { # DNF 4 (python plugin) and DNF 5 (actions plugin): whichever plugin directory exists
    local done=0
    if [[ -d "$(rp /etc/dnf/plugins/post-transaction-actions.d)" ]]; then
        put_text /etc/dnf/plugins/post-transaction-actions.d/m3e-gdm.action 644 <<EOT
# m3e-gnome: rebuild the GDM login-screen resource after gnome-shell changes
gnome-shell:in:$HOOK_CMD refresh --quiet
EOT
        done=1
    fi
    if [[ -d "$(rp /etc/dnf/libdnf5-plugins/actions.d)" ]]; then
        put_text /etc/dnf/libdnf5-plugins/actions.d/m3e-gdm.actions 644 <<EOT
# m3e-gnome: rebuild the GDM login-screen resource after gnome-shell changes
post_transaction:gnome-shell:in::$HOOK_CMD refresh --quiet
EOT
        done=1
    fi
    ((done)) || warn "no dnf actions plugin directory found: install python3-dnf-plugin-post-transaction-actions (DNF 4) or libdnf5-plugin-actions (DNF 5), re-run, or run 'sudo m3e-gdm refresh' after each gnome-shell update"
}

put_text() { # logical-dest mode (content on stdin)
    local dest=$1 mode=$2 tmp
    make_work; tmp=$REPLY/content
    cat >"$tmp"
    claim_dest "$dest"
    put_atomic "$tmp" "$dest" "$mode"
}

hooks_apply() {
    case "$(os_family)" in
        debian) [[ -d "$(rp /etc/apt/apt.conf.d)" ]] && hook_apt ;;
        arch) hook_pacman ;;
        fedora) hook_dnf ;;
        suse) warn "openSUSE has no refresh hook yet (needs a contributor): run 'sudo m3e-gdm refresh' after each gnome-shell update" ;;
        *) warn "unknown distribution: no refresh hook installed; run 'sudo m3e-gdm refresh' after each gnome-shell update" ;;
    esac
    return 0
}
