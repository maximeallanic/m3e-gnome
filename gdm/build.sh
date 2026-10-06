# shellcheck shell=bash
# Build and verify the greeter's gnome-shell-theme.gresource from the STOCK resource plus the staged (validated) data.
# Requires common.sh. Everything happens in a root-owned temporary directory; nothing from the user is executed.

# build_resource STOCK DATA_DIR OUT : writes OUT, dies unless the result passes the checks below.
build_resource() {
    local stock=$1 data=$2 out=$3 w r rel css has_bg=0
    [[ -f "$stock" && ! -L "$stock" ]] || die "stock resource not found: $stock"
    make_work; w=$REPLY
    mkdir -p -- "$w/theme"
    [[ -f "$data/background.png" ]] && has_bg=1

    local list
    list=$(gresource list "$stock") || die "cannot read the stock resource $stock"
    while IFS= read -r r; do
        [[ "$r" == "$GRES_PREFIX"/* && "$r" =~ ^[A-Za-z0-9._/-]+$ && "$r" != *..* ]] ||
            die "unexpected resource name in the stock gresource: $r"
        rel=${r#"$GRES_PREFIX"/}
        mkdir -p -- "$w/theme/$(dirname -- "$rel")"
        gresource extract "$stock" "$r" >"$w/theme/$rel"
    done <<<"$list"

    for css in gnome-shell-light.css gnome-shell-dark.css; do
        [[ -f "$w/theme/$css" ]] || die "the stock resource has no $css: GNOME Shell layout changed, refusing"
        if grep -qF -- "$MARKER" "$w/theme/$css"; then die "the stock resource already carries the m3e-gnome marker: not a stock file"; fi
        cp -- "$w/theme/$css" "$w/orig-$css"
        {
            cat -- "$w/orig-$css"
            printf '\n%s\n' "$MARKER"
            cat -- "$data/theme.css"
            printf '\n'
            if ((has_bg)); then
                printf '#lockDialogGroup { background-image: url("file://%s"); background-size: cover; }\n' "$BG_LOGICAL"
            fi
        } >"$w/theme/$css"
    done

    {
        echo '<?xml version="1.0" encoding="UTF-8"?>'
        echo "<gresources><gresource prefix=\"$GRES_PREFIX\">"
        (cd "$w/theme" && find . -type f | sed 's|^\./||' | LC_ALL=C sort | sed 's|.*|<file>&</file>|')
        echo '</gresource></gresources>'
    } >"$w/theme.gresource.xml"
    glib-compile-resources --sourcedir="$w/theme" --target="$w/built.gresource" "$w/theme.gresource.xml" ||
        die "glib-compile-resources failed"
    verify_resource "$stock" "$w/built.gresource" "$w" "$has_bg" "$data"
    install -m 644 -- "$w/built.gresource" "$out"
}

# verify_resource STOCK BUILT WORK HAS_BG DATA
verify_resource() {
    local stock=$1 built=$2 w=$3 has_bg=$4 data=$5 r css want have
    want=$(gresource list "$stock" | LC_ALL=C sort)
    have=$(gresource list "$built" | LC_ALL=C sort) || die "the compiled resource cannot be listed"
    [[ "$want" == "$have" ]] || die "the compiled resource does not list exactly the stock resources"
    while IFS= read -r r; do
        case "$r" in
            */gnome-shell-light.css|*/gnome-shell-dark.css) continue ;;
        esac
        cmp -s <(gresource extract "$stock" "$r") <(gresource extract "$built" "$r") ||
            die "a non-stylesheet resource differs from the stock one: $r"
    done <<<"$want"
    for css in gnome-shell-light.css gnome-shell-dark.css; do
        gresource extract "$built" "$GRES_PREFIX/$css" >"$w/check-$css"
        [[ "$(grep -cF -- "$MARKER" "$w/check-$css")" == 1 ]] || die "$css: marker missing or repeated"
        cmp -s -n "$(wc -c <"$w/orig-$css")" "$w/orig-$css" "$w/check-$css" || die "$css: stock sheet is not preserved at the start"
        cmp -s <(tail -c +"$(($(wc -c <"$w/orig-$css") + 1))" "$w/check-$css" | tail -n +3 | head -c "$(wc -c <"$data/theme.css")") "$data/theme.css" ||
            die "$css: staged stylesheet not found verbatim after the marker"
        if ((has_bg)); then grep -qF -- "url(\"file://$BG_LOGICAL\")" "$w/check-$css" || die "$css: background rule missing"; fi
    done
}

# Current stock and built identities, recorded in the state directory.
record_identity() { # stock-sha built-sha (taken BEFORE the live file is replaced)
    ((DRY_RUN)) && return 0
    printf '%s\n' "$1" >"$STATE/stock.sha256"
    printf '%s\n' "$2" >"$STATE/built.sha256"
    chmod 644 -- "$STATE/stock.sha256" "$STATE/built.sha256"
}
