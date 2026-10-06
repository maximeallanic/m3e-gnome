# shellcheck shell=bash
# Pinned downloads. Git sources are fetched at one exact commit (shallow) and checked; files are checked against a
# sha256. Nothing is retried silently: a failed or mismatching download stops the install with the reason.
# Requires common.sh.

is_sha1() { [[ "$1" =~ ^[0-9a-f]{40}$ ]]; }

# fetch_git NAME URL REV -> $SRC_DIR/NAME checked out at REV (a 40-hex commit, or a branch/tag with a warning).
fetch_git() {
    local name="$1" url="$2" rev="$3" dir="$SRC_DIR/$1"
    if ((DRY_RUN)); then msg_info "[dry-run] fetch $name $rev from $url"; return 0; fi
    mkdir_owned "$SRC_DIR"
    if ! is_sha1 "$rev"; then
        msg_warn "$name is not pinned to a commit (ref '$rev'): its content cannot be verified"
    fi
    if ! { is_sha1 "$rev" && [[ -d "$dir/.git" ]] && git -C "$dir" cat-file -e "$rev^{commit}" 2>/dev/null; }; then
        git init -q -- "$dir"
        git -C "$dir" fetch -q --depth 1 -- "$url" "$rev" || die "cannot fetch $rev from $url"
        rev="$(git -C "$dir" rev-parse FETCH_HEAD)"
    fi
    git -C "$dir" -c advice.detachedHead=false checkout -q --force --detach "$rev"
    [[ "$(git -C "$dir" rev-parse HEAD)" == "$rev" ]] || die "$name: checked out commit differs from the pin"
    msg_info "$name @ ${rev:0:12}"
}

sha256_of() { sha256sum -- "$1" | cut -d' ' -f1; }

# download_verified URL DEST SHA256 (DEST is written only when the checksum matches).
download_verified() {
    local url="$1" dest="$2" sha="$3" tmp
    if ((DRY_RUN)); then msg_info "[dry-run] download $url (sha256 $sha)"; return 0; fi
    if [[ -f "$dest" && "$(sha256_of "$dest")" == "$sha" ]]; then return 0; fi
    mkdir -p -- "$(dirname -- "$dest")"
    tmp="$dest.part"
    curl -fsSL --proto '=https,file' -o "$tmp" -- "$url" || { rm -f -- "${tmp:?}"; die "download failed: $url"; }
    if [[ "$(sha256_of "$tmp")" != "$sha" ]]; then
        rm -f -- "${tmp:?}"
        die "unexpected sha256 for $url (expected $sha)"
    fi
    mv -- "$tmp" "$dest"
}
