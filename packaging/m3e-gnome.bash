# shellcheck shell=bash
# Bash completion for m3e-gnome-install, m3e-gnome-uninstall and m3e-gnome-verify (flags only).
# tests/test_deb.sh checks that these lists match the --help text of the scripts.
_m3e_gnome() {
    local cur prev flags steps="gtk-theme icons cursor sounds font palette extensions"
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD - 1]}"
    case "${COMP_WORDS[0]##*/}" in
        m3e-gnome-install)
            flags="--dry-run -y --yes --install-deps --dark --light --keep-color-scheme --cursor --no-extensions
                --extensions-only --extensions-dir --skip --no-session-check --gdm --gdm-only --gdm-image --gdm-force
                --uninstall --version -h --help" ;;
        m3e-gnome-uninstall) flags="--dry-run -y --yes --gdm -h --help" ;;
        m3e-gnome-verify)
            flags="--skip --no-extensions --extensions-only --cursor --no-service --gdm --strict -h --help" ;;
        *) return 0 ;;
    esac
    case "$prev" in
        --cursor) mapfile -t COMPREPLY < <(compgen -W "black white" -- "$cur"); return 0 ;;
        --skip) mapfile -t COMPREPLY < <(compgen -W "$steps" -- "$cur"); return 0 ;;
        --extensions-dir) mapfile -t COMPREPLY < <(compgen -d -- "$cur"); return 0 ;;
        --gdm-image) mapfile -t COMPREPLY < <(compgen -f -- "$cur"); return 0 ;;
    esac
    # shellcheck disable=SC2207,SC2086  # flags is a word list on purpose
    mapfile -t COMPREPLY < <(compgen -W "$flags" -- "$cur")
}
complete -F _m3e_gnome m3e-gnome-install m3e-gnome-uninstall m3e-gnome-verify
