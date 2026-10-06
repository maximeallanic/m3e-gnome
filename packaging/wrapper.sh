#!/bin/sh
# @NAME@: runs @SCRIPT@ of the m3e-gnome package (installed under /usr/share/m3e-gnome) as the current user.
# The installer changes only your own home directory and uses sudo by itself for the opt-in GDM step, so it must not
# be started as root.
if [ "$(id -u)" = 0 ]; then
    echo "@NAME@: run this as your own user, not as root (it changes your home directory; --gdm asks for sudo itself)." >&2
    exit 1
fi
here="$(dirname -- "$(readlink -f -- "$0")")"
exec /bin/bash "$here/../share/m3e-gnome/@SCRIPT@" "$@"
