# shellcheck shell=bash
# Ownership tracking. Everything the installer creates is recorded in $STATE_DIR/manifest so that uninstall removes
# exactly those paths and nothing else:
#   F <path>   file or symlink created by us
#   T <path>   directory tree that belongs to us as a whole (removed recursively)
#   D <path>   empty directory we had to create (removed when empty, deepest first)
# A pre-existing path that we are about to replace is first moved into the backup directory (see backup.sh).
# Requires common.sh (init_paths, run, die, msg_*).

MANIFEST=''
declare -A OWNED_F=() OWNED_T=() OWNED_D=() DRY_CREATED=()
PENDING_DIRS=()

# Create the state directory (recording the ancestors we create) and load the manifest.
m_init() {
    MANIFEST="$STATE_DIR/manifest"
    local missing=() d="$STATE_DIR"
    while [[ ! -d "$d" && "$d" != / ]]; do missing=("$d" "${missing[@]}"); d="$(dirname -- "$d")"; done
    if ((DRY_RUN)); then
        m_load
        return 0
    fi
    mkdir -p -- "$STATE_DIR"
    touch -- "$MANIFEST"
    m_load
    local m
    for m in "${missing[@]}"; do
        [[ "$m" == "$STATE_DIR" ]] || m_record D "$m"
    done
}

m_load() {
    OWNED_F=(); OWNED_T=(); OWNED_D=()
    [[ -f "$MANIFEST" ]] || return 0
    local t p
    while IFS=$'\t' read -r t p; do
        case "$t" in F) OWNED_F[$p]=1 ;; T) OWNED_T[$p]=1 ;; D) OWNED_D[$p]=1 ;; esac
    done <"$MANIFEST"
}

m_record() { # F|T|D path
    local t="$1" p="$2"
    ((DRY_RUN)) && return 0
    [[ "$p" != *$'\n'* && "$p" != *$'\t'* ]] || die "path with a tab or newline is not supported: $p"
    case "$t" in
        F) [[ -z "${OWNED_F[$p]:-}" ]] || return 0; OWNED_F[$p]=1 ;;
        T) [[ -z "${OWNED_T[$p]:-}" ]] || return 0; OWNED_T[$p]=1 ;;
        D) [[ -z "${OWNED_D[$p]:-}" ]] || return 0; OWNED_D[$p]=1 ;;
        *) die "bad manifest type: $t" ;;
    esac
    printf '%s\t%s\n' "$t" "$p" >>"$MANIFEST"
}

is_owned() { # true when path is a recorded file/tree or inside a recorded tree
    local p="$1" q
    [[ -n "${OWNED_F[$p]:-}" || -n "${OWNED_T[$p]:-}" ]] && return 0
    q="$p"
    while [[ "$q" != / && "$q" != . ]]; do
        q="$(dirname -- "$q")"
        [[ -n "${OWNED_T[$q]:-}" ]] && return 0
    done
    return 1
}

# mkdir -p that records every directory it creates.
mkdir_owned() {
    local target="$1" missing=() d="$1" m
    while [[ ! -e "$d" && ! -L "$d" && -z "${DRY_CREATED[$d]:-}" && "$d" != / ]]; do missing=("$d" "${missing[@]}"); d="$(dirname -- "$d")"; done
    ((${#missing[@]})) || return 0
    if ((DRY_RUN)); then
        msg_info "[dry-run] mkdir -p $target"
        for m in "${missing[@]}"; do DRY_CREATED[$m]=1; done
        return 0
    fi
    mkdir -p -- "$target"
    for m in "${missing[@]}"; do m_record D "$m"; done
}

# Make room for a path we are about to write: if something we do not own is there, move it to the backup.
claim() {
    local p="$1"
    [[ -e "$p" || -L "$p" ]] || return 0
    is_owned "$p" && return 0
    backup_move "$p"
}

put_file() { # src dest mode
    local src="$1" dest="$2" mode="$3"
    mkdir_owned "$(dirname -- "$dest")"
    claim "$dest"
    if ((DRY_RUN)); then msg_info "[dry-run] install $dest"; return 0; fi
    m_record F "$dest"   # recorded before the write: an interrupted run must not leave an unknown file behind
    install -m "$mode" -- "$src" "$dest"
}

put_text() { # dest mode  (content on stdin)
    local dest="$1" mode="$2" tmp
    make_tmp; tmp="$REPLY"
    cat >"$tmp/content"
    put_file "$tmp/content" "$dest" "$mode"
}

put_link() { # target dest
    local target="$1" dest="$2"
    mkdir_owned "$(dirname -- "$dest")"
    claim "$dest"
    if ((DRY_RUN)); then msg_info "[dry-run] ln -s $target $dest"; return 0; fi
    m_record F "$dest"
    ln -sfn -- "$target" "$dest"
}

# Mirror a directory (rsync --delete: the destination is ours as a whole). Extra arguments go to rsync.
put_tree() { # src dest [rsync args...]
    local src="$1" dest="$2"
    shift 2
    mkdir_owned "$(dirname -- "$dest")"
    claim "$dest"
    if ((DRY_RUN)); then msg_info "[dry-run] rsync $src/ -> $dest/"; return 0; fi
    [[ -d "$src" ]] || die "source directory missing: $src"
    m_record T "$dest"
    rsync -a --delete "$@" -- "$src/" "$dest/"
}

# For trees produced by a build tool: claim (and record) the destination before running the tool.
claim_tree() { mkdir_owned "$(dirname -- "$1")"; claim "$1"; m_record T "$1"; }
record_tree() { [[ -d "$1" ]] && m_record T "$1"; return 0; }
record_file() { [[ -e "$1" || -L "$1" ]] && m_record F "$1"; return 0; }

# --- removal (uninstall) ------------------------------------------------------------------------------------------
# Remove exactly what the manifest lists. Every path is checked to be inside $HOME first.
# Files and trees first; the directories we created are only collected (PENDING_DIRS) and removed afterwards by
# m_remove_dirs, once the state directory itself is gone, so that they can be empty.
m_remove_all() {
    [[ -f "$MANIFEST" ]] || { msg_info "no manifest at $MANIFEST: nothing to remove"; return 0; }
    local t p
    PENDING_DIRS=()
    while IFS=$'\t' read -r t p; do
        [[ -n "$p" ]] || continue
        assert_inside_home "$p"
        case "$t" in
            F) if [[ -e "$p" || -L "$p" ]]; then run rm -f -- "${p:?}"; fi ;;
            T) if [[ -e "$p" || -L "$p" ]]; then run rm -rf -- "${p:?}"; fi ;;
            D) PENDING_DIRS+=("$p") ;;
            *) die "corrupt manifest line: $t $p" ;;
        esac
    done <"$MANIFEST"
}

# Directories we created, deepest first; one that is no longer empty is in use by something else: keep it.
m_remove_dirs() {
    local p
    ((${#PENDING_DIRS[@]})) || return 0
    while IFS= read -r p; do
        [[ -d "$p" ]] || continue
        if ((DRY_RUN)); then
            msg_info "[dry-run] rmdir $p (if empty)"
        elif ! rmdir -- "${p:?}" 2>/dev/null; then
            msg_info "kept (not empty): $p"
        fi
    done < <(printf '%s\n' "${PENDING_DIRS[@]}" | sort -r)
}
