# shellcheck shell=bash
# Uninstall: undo exactly what the manifest and the backup record. Requires common.sh, manifest.sh, backup.sh.

do_uninstall() {
    [[ -d "$STATE_DIR" && -f "$STATE_DIR/manifest" ]] || { msg_info "nothing to uninstall (no $STATE_DIR/manifest)"; return 0; }
    assert_inside_home "$STATE_DIR"
    MANIFEST="$STATE_DIR/manifest"
    STATE_FILE="$STATE_DIR/state"
    backup_init
    msg_step "Uninstalling m3e-gnome"
    msg_info "this removes the files listed in $MANIFEST and restores your previous settings"
    if ((! DRY_RUN)) && ! confirm "Continue?"; then die "aborted (use --yes to skip this question)"; fi

    if [[ "$(state_get service)" == enabled ]]; then
        run systemctl --user disable --now material-sync.service
    fi
    local added
    added="$(state_get added_extensions)"
    if [[ -n "$added" ]]; then
        # shellcheck disable=SC2086  # UUIDs never contain spaces
        run python3 "$EXT_HELPER_PY" remove $added >/dev/null
    fi
    m_remove_all
    if have systemctl; then run systemctl --user daemon-reload; fi

    local restore_failed=0
    if [[ -n "$BACKUP_DIR" && -x "$BACKUP_DIR/restore.sh" ]]; then
        msg_step "Restoring your previous files and settings"
        if ((DRY_RUN)); then
            msg_info "[dry-run] $BACKUP_DIR/restore.sh"
        else
            bash "$BACKUP_DIR/restore.sh" || restore_failed=1
        fi
    fi
    if ((DRY_RUN)); then m_remove_dirs; return 0; fi
    if ((restore_failed)); then
        msg_warn "some items could not be restored; the backup is kept in $BACKUP_DIR (see the messages above)"
        return 1
    fi
    rm -rf -- "${STATE_DIR:?}"
    m_remove_dirs
    msg_step "Done"
    msg_info "Log out and back in to reload the Shell and your applications."
}
