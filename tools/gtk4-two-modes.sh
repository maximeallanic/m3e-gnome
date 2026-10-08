#!/bin/sh
# Rewrites Material-Gnome's GTK 4 matugen template (gtk-4.0/colors-template.css) so that the colors.css matugen
# renders from it holds BOTH palettes: light values by default, dark values inside @media (prefers-color-scheme: dark).
#
# Why: the upstream template only emits the current mode ({{colors.X.default.hex}}), and GTK 4 never re-reads
# gtk.css, so every running GTK 4 app (Chrome included) kept the palette of the mode it was started in. GTK >= 4.20
# evaluates @media (prefers-color-scheme) in the user gtk.css live, for custom properties and @define-color alike
# (checked on GTK 4.24). GTK 3 has no media queries: its apps keep the mode they were started in.
#
# Usage: gtk4-two-modes.sh <path to gtk-4.0/colors-template.css>   (idempotent; the installer runs it after copying
# Material-Gnome, then matugen renders colors.css from the rewritten template)
set -eu
[ $# -eq 1 ] || { echo "usage: $0 <gtk-4.0/colors-template.css>" >&2; exit 2; }
template=$1
grep -q 'prefers-color-scheme' "$template" && exit 0
# The rewrite assumes the upstream layout: a comment header, then the rules (from ":root {" on) written with the
# matugen ".default." mode. Refuse anything else instead of producing a template that silently lost its rules.
grep -q '^:root' "$template" || { echo "$0: no ':root' rule in $template (unexpected Material-Gnome template)" >&2; exit 1; }
grep -q '\.default\.' "$template" || { echo "$0: no '.default.' colour in $template (unexpected Material-Gnome template)" >&2; exit 1; }
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
# Header (everything before the first rule) kept as is; the rules are emitted twice.
{
    sed -n '/^:root/q;p' "$template"
    sed -n '/^:root/,$p' "$template" | sed 's/\.default\./.light./g'
    printf '\n@media (prefers-color-scheme: dark) {\n'
    sed -n '/^:root/,$p' "$template" | sed 's/\.default\./.dark./g'
    printf '}\n'
} >"$tmp"
# Written in place (not moved) so that the file keeps its owner and mode.
cat "$tmp" >"$template"
