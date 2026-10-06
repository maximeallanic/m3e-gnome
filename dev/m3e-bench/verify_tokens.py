#!/usr/bin/env python3
"""Checks that every value of the m3e stylesheets matches the token cited in its trailing comment.

Usage: verify_tokens.py [--compare-blocks] <m3e-tokens.json> <sheet.css>...
Dialect chosen by the file name: "gtk3" -> GTK 3, "gtk4" -> GTK 4, otherwise St (Shell sheet, matugen template).

Comment vocabulary (trailing, on the declaration line):
  /* Component.Key [Component.Key ...] */   tokens of m3e-tokens.json matched, in order, with the numbers of the value;
                                            a typography token takes a suffix .size, .line_height, .weight, .tracking;
                                            a "dp" token of 0 matches a 0 (or a missing number); a "shape" token
                                            (full) matches any value >= 999; "corners" and "curve" take four numbers.
  /* Component.Key@value */                 pinned token: the token must equal `value` AND `value` must appear on the
                                            declaration, at any position (every occurrence is consumed). For a token
                                            that is only one number among many (an opacity inside a gradient). It may
                                            follow other tokens, or sit in an M3E-visual comment after the reason.
  /* M3E-visual: <reason> */                value with no token (reason required): numbers are not checked
                                            (except the pinned ones, which are verified and removed first).
  /* important-exception: <reason> */       St only: authorises !important on that declaration (reason required);
                                            its numbers stay subject to the tokens (the comment cites none).
Every colour must be a palette reference (@role, var(--role) in GTK 4, matugen {{...}} in St); a hard-coded colour is
refused. GTK 3 refuses var().

St dialect, in addition: the matugen {{...}} are palette colours (rgba({{r}}, {{g}}, {{b}}, a) = role with opacity a, a
checked as a number); no font-weight above 400 (401-599, bold, bolder included, also in the shorthand `font:`);
!important is refused except in the no-bold rule (`* { font-weight: normal !important; }`), on `border: none` in the
"Flat surfaces" block (the one exception the sheet header documents: the stock sheet sets the border per state with
more specific selectors) and on a declaration with an important-exception comment. Declarations of a rule written on a single line (`sel { prop: val; }`) or glued to a
brace are checked like the others; the trailing comment only counts for a lone declaration.

--compare-blocks: also compares the "/* == Title == */" block titles of the GTK 3 sheets with those of the GTK 4
sheets (same titles, same order). Off by default: the theme splits each toolkit into its own concern parts.
"""
import json
import re
import sys
from pathlib import Path

DECL = re.compile(r"^\s*(-?[a-z][-a-z]*)\s*:\s*([^;{}]*);\s*(?:/\*(.*?)\*/)?\s*$")
PIN = re.compile(r"(?<![\w.@])([A-Za-z]\w*(?:\.\w+){1,2})@(-?\d+(?:\.\d+)?)(?![\w.])")
NUMBER = re.compile(r"(?<![\w#.-])-?\d+(?:\.\d+)?(?![\d.]*%)")  # percentages (positions) are not tokens
TITLE = re.compile(r"/\*\s*==\s*(.*?)\s*==\s*\*/")
MATUGEN = r"\{\{[^{}]*\}\}"
MATUGEN_RGBA = re.compile(rf"rgba\(\s*{MATUGEN}\s*,\s*{MATUGEN}\s*,\s*{MATUGEN}\s*,")
BOLD_WORD = re.compile(r"\b(bold|bolder)\b")
SHORTHAND_WEIGHT = re.compile(r"(?<![\w.#-])(\d{3,4})(?![\w.%])")  # unitless weight in `font:`
VISUAL = "M3E-visual:"
IMPORTANT_EXCEPTION = "important-exception:"
FLAT_SURFACES_BLOCK = "Flat surfaces"
NAMED_COLORS = {"white", "black", "red", "green", "blue", "gray", "grey", "yellow", "orange", "purple",
                "pink", "cyan", "magenta", "brown"}


def _token(tokens, ref):
    parts = ref.split(".")
    if len(parts) not in (2, 3):
        return None
    t = tokens.get(parts[0], {}).get(parts[1])
    if t is None or len(parts) == 2:
        return t
    if t["type"] != "typography" or parts[2] not in t["value"]:
        return None
    return {"type": "number", "value": t["value"][parts[2]]}


def _check_numbers(numbers, refs, tokens, prop):
    """Matches the tokens with the numbers, in order. Returns a list of messages."""
    errors, i = [], 0
    for ref in refs:
        t = _token(tokens, ref)
        if t is None:
            errors.append(f"unknown token: {ref}")
            continue
        width = 4 if t["type"] in ("corners", "curve") else 1
        if width == 1 and t["type"] == "dp" and t["value"] == 0:
            if any(x != 0 for x in numbers[i:i + 1]):
                errors.append(f"{ref}: {numbers[i]:g} instead of 0")
            i += 1
            continue
        if width == 1:
            while i < len(numbers) and numbers[i] == 0:
                i += 1
        chunk = numbers[i:i + width]
        i += width
        if len(chunk) < width:
            errors.append(f"{ref}: no matching value")
            continue
        if t["type"] == "shape":
            if chunk[0] < 999:
                errors.append(f"{ref} (full): {chunk[0]:g} < 999")
            continue
        expected = t["value"] if width == 4 else [t["value"]]
        if any(abs(a - b) > 1e-6 for a, b in zip(chunk, expected)):
            errors.append(f"{ref}: {' '.join(f'{x:g}' for x in chunk)} instead of "
                          f"{' '.join(f'{x:g}' for x in expected)}")
    rest = [x for x in numbers[i:] if x != 0 and not (prop == "opacity" and x == 1)]
    if rest:
        errors.append(f"value with no token: {' '.join(f'{x:g}' for x in rest)}")
    return errors


def _check_pins(pins, numbers, tokens):
    """Pinned tokens (`Token@value`): verifies each token against its value, and that the value is on the declaration.
    Returns (messages, numbers without the pinned values)."""
    errors = []
    for ref, raw in pins:
        t, value = _token(tokens, ref), float(raw)
        if t is None:
            errors.append(f"unknown token: {ref}")
        elif t["type"] == "dp" and t["value"] == 0 or t["type"] in ("shape", "corners", "curve"):
            errors.append(f"{ref}@{raw}: only a scalar token can be pinned")
        elif abs(t["value"] - value) > 1e-6:
            errors.append(f"{ref}@{raw}: the token is {t['value']:g}")
        elif value not in numbers:
            errors.append(f"{ref}@{raw}: {raw} is not on the declaration")
        else:
            numbers = [x for x in numbers if x != value]
    return errors, numbers


def _matugen(value):
    """St dialect: rgba({{r}}, {{g}}, {{b}}, a) -> alpha(@matugen, a); {{...}} -> @matugen."""
    return re.sub(MATUGEN, "@matugen", MATUGEN_RGBA.sub("alpha(@matugen,", value))


def _has_exception(comment):
    """Is `comment` an important-exception comment with its reason?"""
    return comment.startswith(IMPORTANT_EXCEPTION) and bool(comment[len(IMPORTANT_EXCEPTION):].strip())


def is_bold(prop, value):
    """True if the declaration sets a weight > 400 (font-weight, or the weight of the font shorthand)."""
    v = value.replace("!important", "").strip().lower()
    if prop == "font-weight":
        return bool(BOLD_WORD.fullmatch(v)) or (v.isdigit() and int(v) > 400)
    if prop == "font":
        return bool(BOLD_WORD.search(v)) or any(int(n) > 400 for n in SHORTHAND_WEIGHT.findall(v))
    return False


# The extensions sheet (dev/m3e-bench-extensions) may use !important everywhere: it must beat third-party sheets.
ALLOW_IMPORTANT = False


def _check_st(prop, value, selector, block, comment=""):
    """Rules specific to the Shell sheet (bold, !important). Returns a list of messages."""
    msgs = []
    if is_bold(prop, value):
        msgs.append(f"font-weight > 400 forbidden (no bold): {value.strip()}")
    if "!important" in value and not ALLOW_IMPORTANT:
        no_bold_rule = selector == "*" and prop == "font-weight" and \
            value.replace("!important", "").strip() == "normal"
        flat_border = block == FLAT_SURFACES_BLOCK and prop == "border" and \
            value.replace("!important", "").strip() == "none"
        if not no_bold_rule and not flat_border and not _has_exception(comment):
            msgs.append("!important forbidden outside the no-bold rule, the flat-surface borders and a marked "
                        "exception (/* important-exception: <reason> */)")
    return msgs


def _check_declaration(prop, value, comment, selector, block, tokens, dialect):
    """Checks one declaration. Returns the list of messages (empty if conforming)."""
    msgs = []
    if dialect == "st":
        msgs += _check_st(prop, value, selector, block, comment)
        if msgs:
            return msgs
        value = value.replace("!important", "")
        if _has_exception(comment):
            comment = ""  # no token cited: every number of the declaration is reported
    if re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", value) or \
            set(re.findall(r"[a-z]+", value.lower())) & NAMED_COLORS:
        msgs.append("hard-coded colour (use a palette variable)")
    if dialect == "gtk3" and re.search(r"\bvar\(", value):
        msgs.append("var() forbidden in GTK 3")
    numbers = [float(x) for x in NUMBER.findall(re.sub(r"(@|--)[\w-]+", "", value))]
    pins = PIN.findall(comment)
    comment = PIN.sub("", comment).strip() if not comment.startswith(VISUAL) else comment
    if pins:
        pin_errors, numbers = _check_pins(pins, numbers, tokens)
        msgs += pin_errors
    if comment.startswith(VISUAL):
        if not comment[len(VISUAL):].strip():
            msgs.append("M3E-visual without a reason")
    elif not any(x.startswith("hard-coded colour") for x in msgs):
        msgs += _check_numbers(numbers, comment.split() if comment else [], tokens, prop)
    return msgs


def _declarations(text):
    """Declarations "prop: value" of a rule fragment glued to a brace (separated by ;)."""
    for chunk in text.split(";"):
        if ":" in chunk:
            prop, value = chunk.split(":", 1)
            if re.fullmatch(r"-?[a-z][-a-z]*", prop.strip()):
                yield prop.strip(), value.strip()


def _logical_lines(css):
    """(line number, text) pairs where a comment spread over several lines is joined into one logical line, so that
    the words of a long comment are never taken for a selector, and a trailing multi-line comment still belongs to
    its declaration."""
    lines = css.splitlines()
    out, i = [], 0
    while i < len(lines):
        no, text = i + 1, lines[i]
        # An opened comment with no closing on the line: join the following lines up to the closing.
        while re.sub(r"/\*.*?\*/", "", text).count("/*") and i + 1 < len(lines):
            i += 1
            text += " " + lines[i].strip()
        out.append((no, text))
        i += 1
    return out


def verify(css, tokens, dialect):
    errors = []
    selector, buffer, in_rule, block = "", "", False, ""

    def check(no, prop, value, comment):
        msgs = _check_declaration(prop, value, comment, selector, block, tokens, dialect)
        if msgs:
            errors.append(f"{no}: {prop}: {' ; '.join(msgs)}")

    for no, line in _logical_lines(css):
        title = TITLE.search(line)
        if title:
            block = title[1]
        source = _matugen(line) if dialect == "st" else line
        m = DECL.match(source)
        if m:
            check(no, m[1], m[2], (m[3] or "").strip())
            continue
        # Structure line: selector (St dialect: the no-bold rule is recognised by its "*" selector), braces, and
        # declarations glued to a brace (single-line rule, "sel { a: b;" ...).
        bare = re.sub(r"/\*.*?\*/", "", source)
        if "{" not in bare and "}" not in bare:
            if bare.strip() and not in_rule:
                buffer += " " + bare.strip()  # selector spread over several lines
            continue
        comments = re.findall(r"/\*(.*?)\*/", source)
        to_check = []  # (prop, value, selector)
        for chunk in re.split(r"([{}])", bare):
            if chunk == "{":
                selector, buffer, in_rule = buffer.strip(), "", True
            elif chunk == "}":
                selector, buffer, in_rule = "", "", False
            elif in_rule:
                to_check += [(p, v, selector) for p, v in _declarations(chunk)]
            elif chunk.strip():
                buffer += " " + chunk.strip()
        comment = comments[-1].strip() if len(to_check) == 1 and comments else ""
        line_selector = selector
        for prop, value, sel in to_check:
            selector = sel
            check(no, prop, value, comment)
        selector = line_selector
    return errors


def compare_blocks(css_a, css_b):
    a, b = TITLE.findall(css_a), TITLE.findall(css_b)
    return [] if a == b else [f"different blocks: {a} / {b}"]


def dialect_of(path):
    name = Path(path).name
    return "gtk3" if "gtk3" in name else "gtk4" if "gtk4" in name else "st"


def main(argv):
    compare = "--compare-blocks" in argv
    args = [a for a in argv if a != "--compare-blocks"]
    if len(args) < 2:
        print("usage: verify_tokens.py [--compare-blocks] <m3e-tokens.json> <sheet.css>...", file=sys.stderr)
        return 2
    tokens = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    sheets = args[1:]
    texts = {f: Path(f).read_text(encoding="utf-8") for f in sheets}
    errors = [f"{f}:{e}" for f in sheets for e in verify(texts[f], tokens, dialect_of(f))]
    if compare:
        gtk3 = "".join(texts[f] for f in sheets if dialect_of(f) == "gtk3")
        gtk4 = "".join(texts[f] for f in sheets if dialect_of(f) == "gtk4")
        if gtk3 and gtk4:
            errors += compare_blocks(gtk3, gtk4)
    print("\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
