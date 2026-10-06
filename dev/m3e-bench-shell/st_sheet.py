#!/usr/bin/env python3
"""Static check of a stylesheet for St (GNOME Shell 50): unknown properties and invalid units.

St SILENTLY ignores a property it does not know (`colour: red`) and a length with an unknown unit (`width: 12qq`):
nothing in shell.log, even with an actor carrying the class. Only syntax errors (and a few non-numeric length values)
leave a trace there; run.sh looks for them with CSS_ERROR_PATTERN. This check covers the rest.

Known properties = those of the stock 50.5 sheets (dev/reference/shell-stock/, Shell-specific properties included) +
those read by St itself (st-theme-node.c) + EXTRA.

Usage: st_sheet.py <sheet.css>...   (prints "file:line: message", exit code 1 if there is an error)
"""
import re, sys
from pathlib import Path

STOCK = Path(__file__).resolve().parent.parent / "reference" / "shell-stock"

# Properties read by St itself (st-theme-node.c, st-theme-node-transitions.c, st-entry.c...).
ST = {
    "background", "background-color", "background-image", "background-position", "background-repeat",
    "background-size", "background-gradient-direction", "background-gradient-start", "background-gradient-end",
    "border", "border-color", "border-width",
    "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
    "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
    "border-radius", "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius",
    "border-bottom-left-radius", "border-image", "outline", "outline-color", "outline-width",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "width", "height", "min-width", "min-height", "max-width", "max-height",
    "color", "font", "font-family", "font-size", "font-style", "font-variant", "font-weight",
    "font-feature-settings", "letter-spacing", "text-align", "text-decoration", "text-shadow",
    "icon-shadow", "icon-size", "box-shadow", "transition-duration", "caret-color", "caret-size",
    "selected-color", "selection-background-color", "warning-color", "error-color", "success-color",
    "-st-icon-style", "-st-hfade-offset", "-st-vfade-offset", "-st-natural-width", "-st-natural-height",
    "-st-background-image-shadow", "spacing",
}
# Per-side border shorthands ("border-bottom: 1px solid c"): St does not draw them, without a message (observed in
# the bench). Refused, with the form to use.
SIDE_BORDERS = {"border-top", "border-right", "border-bottom", "border-left"}
# Properties read by the JS of the Shell or of active extensions, absent from the stock sheets: the status-bar
# extension (battery.js) reads these two with get_theme_node().get_length() / lookup_color().
EXTRA = {"-status-bar-height", "-status-bar-low"}
# Length, duration and angle units understood by St (libcroco + st-theme-node.c).
UNITS = {"px", "pt", "em", "%", "mm", "cm", "in", "pc", "ms", "s", "deg", "rad"}
# Value functions understood by St (calc() is not: "Ignoring length property that isn't a number").
FUNCTIONS = {"rgb", "rgba", "hsl", "hsla", "url", "st-darken", "st-lighten", "st-mix", "st-transparentize",
             "cubic-bezier"}


def _strip_comments(text):
    # Replaces each comment with as many newlines as it contains (line numbers kept).
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def known_properties():
    known = set(ST) | EXTRA
    for f in sorted(STOCK.glob("gnome-shell-*.css")):
        for _, prop, _ in _declarations(f.read_text(encoding="utf-8")):
            known.add(prop)
    return known - SIDE_BORDERS


def _declarations(text):
    """(line, property, value) of each declaration of the { ... } blocks."""
    text = _strip_comments(text)
    for m in re.finditer(r"\{([^{}]*)\}", text):
        block = m.group(1)
        start = text.count("\n", 0, m.start(1)) + 1
        pos = 0
        for decl in block.split(";"):
            # Line of the first non-blank character of the declaration.
            line = start + block.count("\n", 0, pos + len(decl) - len(decl.lstrip()))
            pos += len(decl) + 1
            if not decl.strip():
                continue
            prop, colon, value = decl.partition(":")
            yield line, (prop.strip().lower() if colon else decl.strip()), value.strip() if colon else None


def errors(text, known=None):
    """"line: message" for each declaration St would ignore."""
    known = known_properties() if known is None else known
    out = []
    for line, prop, value in _declarations(text):
        if value is None:
            out.append(f"{line}: declaration without ':': {prop!r}")
            continue
        if prop in SIDE_BORDERS:
            out.append(f"{line}: per-side border shorthand ignored by St: {prop} (use {prop}-width and {prop}-color)")
        elif prop not in known:
            out.append(f"{line}: property unknown to St: {prop}")
        for f in re.findall(r"(?<![\w-])([A-Za-z_-][\w-]*)\(", value):
            if f.lower() not in FUNCTIONS:
                out.append(f"{line}: function unknown to St: {prop}: {f}()")
        # Percentage outside the arguments of a function (st-mix(..., 60%) is valid): St writes it
        # ("percentage lengths not currently supported") and ignores the length.
        outside = re.sub(r"\"[^\"]*\"|'[^']*'", " ", value)
        while re.search(r"\([^()]*\)", outside):
            outside = re.sub(r"\([^()]*\)", " ", outside)
        if re.search(r"\d%", outside):
            out.append(f"{line}: length percentage not supported by St: {prop}: {value}")
        v = re.sub(r"url\([^)]*\)|\"[^\"]*\"|'[^']*'|#[0-9a-fA-F]+\b", " ", value)
        for number, unit in re.findall(r"(?<![\w.-])(\d*\.?\d+)([a-zA-Z_%][\w%-]*)", v):
            if unit.lower() not in UNITS:
                out.append(f"{line}: unit unknown to St: {prop}: {number}{unit}")
    return out


def main(paths):
    known = known_properties()
    code = 0
    for p in paths:
        for e in errors(Path(p).read_text(encoding="utf-8"), known):
            print(f"{p}:{e}")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
