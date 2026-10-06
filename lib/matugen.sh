# shellcheck shell=bash
# matugen (https://github.com/InioX/matugen, GPL-2.0, Rust): the template engine that renders the palette into the
# theme. Search result: maintained (v4.2.0 released 2026-08-17), official release binary for x86_64 with a published
# sha256, also on crates.io and as AUR matugen-bin. Adopted as is, not reimplemented.
# Requires common.sh, manifest.sh, fetch.sh, pins.sh.

MATUGEN_BIN=''

version_ge() { # a b -> true when a >= b (dotted numeric versions)
    [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n 1)" == "$2" ]]
}

matugen_version_ok() { # path -> 0 when it is a matugen of the accepted range
    local v
    v="$("$1" --version 2>/dev/null | sed -n 's/^matugen \([0-9][0-9.]*\).*/\1/p')" || return 1
    [[ -n "$v" ]] || return 1
    [[ "${v%%.*}" == "${MATUGEN_VERSION%%.*}" ]] && version_ge "$v" "$MATUGEN_MIN_VERSION"
}

ensure_matugen() {
    local found tmp dir
    found="$(command -v matugen || true)"
    [[ -z "$found" && -x "$BIN_DIR/matugen" ]] && found="$BIN_DIR/matugen"
    if [[ -n "$found" ]] && matugen_version_ok "$found"; then
        MATUGEN_BIN="$found"
        msg_info "matugen: using $found"
        # The user service only searches ~/.local/bin, /usr/local/bin, /usr/bin and /bin (material-sync.service).
        case "$(dirname -- "$found")" in
            "$BIN_DIR"|/usr/local/bin|/usr/bin|/bin) ;;
            *) put_link "$found" "$BIN_DIR/matugen"; MATUGEN_BIN="$BIN_DIR/matugen" ;;
        esac
        return 0
    fi
    [[ -n "$found" ]] && msg_warn "matugen at $found is not version $MATUGEN_MIN_VERSION or newer (same major): installing $MATUGEN_VERSION"
    case "$(uname -m)" in
        x86_64) ;;
        *) die "no matugen $MATUGEN_VERSION release binary for $(uname -m). Build it: cargo install matugen --version $MATUGEN_VERSION --locked (then re-run), or see https://github.com/InioX/matugen" ;;
    esac
    if ((DRY_RUN)); then
        msg_info "[dry-run] download matugen $MATUGEN_VERSION to $BIN_DIR/matugen (sha256 $MATUGEN_SHA256_X86_64)"
        return 0
    fi
    mkdir_owned "$M3E_CACHE"
    dir="$M3E_CACHE/downloads"
    mkdir -p -- "$dir"
    download_verified "$MATUGEN_URL_X86_64" "$dir/matugen-$MATUGEN_VERSION-x86_64.tar.gz" "$MATUGEN_SHA256_X86_64"
    [[ "$(tar -tzf "$dir/matugen-$MATUGEN_VERSION-x86_64.tar.gz")" == matugen ]] ||
        die "unexpected content in the matugen archive"
    make_tmp; tmp="$REPLY"
    tar -xzf "$dir/matugen-$MATUGEN_VERSION-x86_64.tar.gz" --no-same-owner -C "$tmp" matugen
    put_file "$tmp/matugen" "$BIN_DIR/matugen" 755
    matugen_version_ok "$BIN_DIR/matugen" || die "the downloaded matugen does not run"
    MATUGEN_BIN="$BIN_DIR/matugen"
    msg_info "matugen $MATUGEN_VERSION installed to $BIN_DIR/matugen"
}
