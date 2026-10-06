# systemd

`material-sync.service`: user unit (`~/.config/systemd/user/`) that runs `material-sync` once at start (a failure there does not
stop the service) and then keeps `material-sync-watch` running. Enable with
`systemctl --user enable --now material-sync.service`. Expects the scripts in `~/.local/bin`.
