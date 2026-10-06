#!/usr/bin/env python3
"""Static check of the extensions stylesheet (theme/shell/m3e-extensions-template.css, or its matugen output).

Same rules as dev/m3e-bench/verify_tokens.py for the St dialect (matugen colours only, no bold, every number carries
its token or `M3E-visual: <reason>`) with one difference: `!important` is allowed on any declaration. Reason (header
of the sheet): in St 50 it is the only way to beat the stylesheet of a third-party extension whatever the load order
and specificity (rank 3N of get_origin, st-theme.c). Then the St-dialect check of dev/m3e-bench-shell/st_sheet.py
(unknown properties, invalid units) with the properties that extensions read through StThemeNode.get_length /
get_color instead of St (Dash to Dock tooltip offset and launcher-API progress bar).

Usage: verify_sheet.py [--tokens m3e-tokens.json] [--template FILE] [--rendered FILE]
(prints "file:line: message"; exit 1 on a deviation). By default: the template of the repository, rendered in dark and
light into a temporary directory by dev/m3e-bench/render_theme.py. Nested-Shell behaviour of Dash to Dock / status-bar is covered by
the `extensions` suite of the m3e-gnome-extensions bench (tests/bench/run.sh --suite extensions).
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "m3e-bench"))
sys.path.insert(0, str(HERE.parent / "m3e-bench-shell"))
import render_theme  # noqa: E402
import st_sheet  # noqa: E402
import verify_tokens  # noqa: E402

DEFAULT_SHEET = REPO / "theme" / "shell" / "m3e-extensions-template.css"
DEFAULT_TOKENS = REPO / "dev" / "reference" / "m3e-tokens.json"
EXTENSION_PROPERTIES = {
    "-x-offset",
    "-progress-bar-track-background", "-progress-bar-track-border",
    "-progress-bar-background", "-progress-bar-border",
}


def token_errors(css, tokens):
    """verify_tokens messages for the St dialect with `!important` allowed."""
    verify_tokens.ALLOW_IMPORTANT = True
    try:
        return verify_tokens.verify(css, tokens, "st")
    finally:
        verify_tokens.ALLOW_IMPORTANT = False


def st_errors(path):
    """St-dialect check (unknown properties, invalid units) of a RENDERED sheet (no matugen expressions left)."""
    st_sheet.EXTRA |= EXTENSION_PROPERTIES
    css = Path(path).read_text(encoding="utf-8")
    return [f"{path}:{e}" for e in st_sheet.errors(css, st_sheet.known_properties())]


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--tokens", default=str(DEFAULT_TOKENS))
    p.add_argument("--template", default=str(DEFAULT_SHEET), help="matugen template (token rules)")
    p.add_argument("--rendered", help="rendered sheet (St dialect); default: rendered here in a temporary directory")
    a = p.parse_args(argv)
    tokens = json.loads(Path(a.tokens).read_text(encoding="utf-8"))
    template = Path(a.template)
    errors = [f"{template}:{e}" for e in token_errors(template.read_text(encoding="utf-8"), tokens)]
    if a.rendered:
        errors += st_errors(a.rendered)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ("dark", "light"):
                out = render_theme.render(Path(tmp) / mode, mode)
                errors += st_errors(out / "m3e-extensions.css")
    if errors:
        print("\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
