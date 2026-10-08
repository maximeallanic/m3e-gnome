"""CSS gate of the m3e-gnome GDM helper: a small tokenizer, and every check runs on its token stream.

Checking CSS with regular expressions over the text is unsound: comment markers inside string literals make a
"strip the comments first" step delete real code, and escapes hide identifiers. This tokenizer follows the CSS
Syntax rules that matter for the decision (comments, strings, identifiers, functions, url() tokens, at-rules,
brackets) and refuses what it cannot classify with certainty:

  - NUL or control characters, unterminated strings, comments and url() tokens;
  - any backslash outside a comment (escapes could spell `url(` or `@import`);
  - unbalanced or mismatched ( ) [ ] { };
  - every at-rule (the stylesheet we install has none; @import in any spelling is one);
  - image functions (image-set, src, image, element, cross-fade, paint, ...);
  - url() other than the staged background or resource:///org/gnome/shell/theme/<name>.svg|png.

Imported by ingest.py (python3 -I, from the root-owned helper directory). Standard library only.
"""
import re

BACKGROUND_URL = "file:///usr/local/share/m3e-gnome/gdm/background.png"
RESOURCE_URL_RE = re.compile(r"^resource:///org/gnome/shell/theme/[A-Za-z0-9_-]+(?:-[A-Za-z0-9_]+)*\.(?:svg|png)$")
FORBIDDEN_FUNCTIONS = {"image-set", "-webkit-image-set", "image", "src", "element", "cross-fade", "paint", "expression",
                       "attr", "local", "-moz-element", "-webkit-cross-fade"}
CLOSERS = {"(": ")", "[": "]", "{": "}"}
IDENT_START = re.compile(r"[A-Za-z_\-]|[^\x00-\x7f]")
IDENT_CHAR = re.compile(r"[A-Za-z0-9_\-]|[^\x00-\x7f]")


class CssRejected(Exception):
    pass


def _bad(msg):
    raise CssRejected(msg)


def _read_string(text, i, quote):
    """text[i] is the opening quote; return (value, index after the closing quote)."""
    j = i + 1
    while j < len(text):
        c = text[j]
        if c == quote:
            return text[i + 1:j], j + 1
        if c == "\\":
            _bad("backslash escape in a string")
        if c in "\n\r\f":
            _bad("unterminated string")
        j += 1
    _bad("unterminated string")


def _skip_space(text, i):
    while i < len(text) and text[i] in " \t\n\r\f":
        i += 1
    return i


def _read_url(text, i):
    """i is just after `url` and optional whitespace, at '('. Return (target, index after ')')."""
    i = _skip_space(text, i + 1)
    if i >= len(text):
        _bad("unterminated url()")
    if text[i] in "\"'":
        target, i = _read_string(text, i, text[i])
        i = _skip_space(text, i)
        if i >= len(text) or text[i] != ")":
            _bad("garbage after the string of a url()")
        return target, i + 1
    j = i
    while j < len(text) and text[j] not in ")":
        if text[j] in " \t\n\r\f\"'(\\":
            _bad("malformed unquoted url()")
        j += 1
    if j >= len(text):
        _bad("unterminated url()")
    return text[i:j], j + 1


def tokenize(text):
    """Yield (kind, value, start, end): kind is comment, string, url, function, ident, atrule, open, close or other
    (one character, whitespace included). Raises CssRejected on anything unsafe or malformed."""
    if "\x00" in text:
        _bad("NUL byte")
    if re.search(r"[\x01-\x08\x0b\x0e-\x1f\x7f]", text):
        _bad("control character")
    stack = []
    i, n = 0, len(text)
    while i < n:
        c, start = text[i], i
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                _bad("unterminated comment")
            kind, value, i = "comment", text[i:end + 2], end + 2
        elif c in "\"'":
            value, i = _read_string(text, i, c)
            kind = "string"
        elif c == "\\":
            _bad("backslash escape outside a comment")
        elif c == "@":
            m = re.compile(r"@[A-Za-z_\-]*").match(text, i)
            kind, value, i = "atrule", m.group(0), m.end()
        elif IDENT_START.match(c) or c.isdigit():
            j = i + 1
            while j < n and IDENT_CHAR.match(text[j]):
                j += 1
            ident = text[i:j]
            k = _skip_space(text, j)
            if k < n and text[k] == "(" and not c.isdigit():
                if ident.lower() == "url":
                    value, i = _read_url(text, k)
                    kind = "url"
                else:
                    stack.append(")")
                    kind, value, i = "function", ident, k + 1
            else:
                kind, value, i = "ident", ident, j
        elif c in CLOSERS:
            stack.append(CLOSERS[c])
            kind, value, i = "open", c, i + 1
        elif c in ")]}":
            if not stack or stack.pop() != c:
                _bad(f"unbalanced '{c}'")
            kind, value, i = "close", c, i + 1
        else:
            kind, value, i = "other", c, i + 1
        yield kind, value, start, i
    if stack:
        _bad("unbalanced brackets at the end of the stylesheet")


def validate_css_text(text):
    code = [(k, v) for k, v, _s, _e in tokenize(text) if k != "comment" and not (k == "other" and v.isspace())]
    if not code:
        _bad("empty stylesheet")
    for kind, value in code:
        if kind == "atrule":
            _bad(f"at-rule {value} is refused")
        elif kind == "function" and value.lower() in FORBIDDEN_FUNCTIONS:
            _bad(f"{value}() is refused")
        elif kind == "url" and value != BACKGROUND_URL and not RESOURCE_URL_RE.match(value):
            _bad(f"url({value[:60]!r}) is outside the theme assets")
    for idx, (kind, _value) in enumerate(code):
        if kind == "url" and idx + 1 < len(code):
            nk, nv = code[idx + 1]
            if not (nk == "close" or (nk == "other" and nv in ";,!")):
                _bad("garbage glued to a url() token")
    # Placeholders of the template engine must have been rendered: two consecutive braces never occur in valid CSS here.
    for (k1, v1), (k2, v2) in zip(code, code[1:]):
        if k1 == "open" and v1 == "{" and k2 == "open" and v2 == "{":
            _bad("unrendered template placeholder")


def strip_comments(text):
    """The stylesheet without its comments (everything else byte for byte); used by the user-side installer."""
    out, pos = [], 0
    for kind, _value, start, end in tokenize(text):
        if kind == "comment":
            out.append(text[pos:start])
            out.append(" ")
            pos = end
    out.append(text[pos:])
    return "".join(out)


def drop_relative_urls(text):
    """The stylesheet without the declarations whose url() is relative (everything else byte for byte); used by the
    user-side installer. A relative url() names a file next to the session stylesheet (~/.themes/M3E-Shell/gnome-shell/
    assets/, e.g. the palette-rendered calendar dots); the greeter's stylesheet lives in the stock gresource, which holds
    no such file, so the declaration is removed and the stock rule it overrode applies again."""
    tokens = list(tokenize(text))
    cuts = []
    for idx, (kind, value, _start, _end) in enumerate(tokens):
        if kind != "url" or ":" in value or value.startswith("/"):
            continue
        b = idx
        while b > 0 and not (tokens[b - 1][0] == "other" and tokens[b - 1][1] == ";") and tokens[b - 1][1] != "{":
            b -= 1
        e = idx
        while e < len(tokens) and not (tokens[e][0] == "other" and tokens[e][1] == ";") and tokens[e][1] != "}":
            e += 1
        if b == 0 or e == len(tokens):
            _bad("relative url() outside a declaration block")
        end = tokens[e][3] if tokens[e][1] == ";" else tokens[e][2]
        cuts.append((tokens[b][2], end))
    out, pos = [], 0
    for start, end in cuts:
        if start < pos:
            continue
        out.append(text[pos:start])
        pos = end
    out.append(text[pos:])
    return "".join(out)
