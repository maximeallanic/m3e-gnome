"""Common ink grid of the symbolic icons, shared by build.py and check_ink_grid.py (docs/design-notes.md, "Ink grid").

Reference: the hand-drawn window buttons (symbolic/actions/window-*): ink 10 px high in a 16 px frame, 1.5 px stroke.
10 px is the cap height of Google Sans Flex at Body medium (0.716 x 14 px). So every icon takes as ink height the cap
height of the text next to it, and as stroke 15 % of that height. Icon files keep their frame (they also serve quick
settings tiles, menus, OSDs and sidebars); each place sets the displayed size in CSS (top bar, GTK header bars), and
the checker reads those sizes back from the stylesheets.

The constants and the weight choice are pure (build.py needs nothing else); the font and stylesheet readers are only
used by check_ink_grid.py.
"""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHELL_CSS_DIR = REPO / 'theme' / 'shell' / 'm3e-shell'
GTK4_CSS_DIR = REPO / 'theme' / 'overrides'

STROKE_RATIO = 1.5 / 10        # stroke / ink height of the window buttons
# Status icons (map.py): every symbol covers STATUS_INK of its frame height, the share they already had in the quick
# settings tiles. The top bar sets the displayed size so their ink lands on the cap height of the clock.
STATUS_INK = 0.72
WEIGHTS = (300, 400, 500, 600, 700)    # Material Symbols weights fetched upstream (<name>_wght<g>_<opsz>px.svg)
STROKE_PROBE = 'remove'                # a lone horizontal bar: its ink height is the stroke of a weight
APP_SQUARE = 'check_box_outline_blank'  # app-icon counterpart of the "maximize" window button

# Selectors whose sizes the grid depends on (check_ink_grid.py reads them; see docs/design-notes.md).
BODY_TEXT = ('stage', 'font-size')                                          # Shell, 00-base.css
CLOCK = ('#panel .panel-button.clock-display .clock', 'font-size')          # Shell, 10-top-bar.css
BAR_ICON = ('#panel .panel-button .system-status-icon', 'icon-size')        # Shell, 10-top-bar.css
HEADER_ICON = ('headerbar button:not(#m3e).image-button', '-gtk-icon-size')  # GTK 4, m3e-gtk4-buttons.css


def status_weight(box, stroke):
    """Weight of a status symbol: the one whose stroke, once the symbol is scaled to STATUS_INK of the frame, comes
    closest to STROKE_RATIO of the ink height. `box` is the symbol's ink box [x, y, w, h] at weight 400 (grid units),
    `stroke(w)` the stroke thickness at weight w. A heavier weight thickens the outline on both sides, so the box is
    estimated by growing it by the stroke difference."""
    _, _, w, h = box
    base = stroke(400)

    def error(weight):
        d = stroke(weight) - base
        return abs(stroke(weight) / max((h + d) / STATUS_INK, w + d) - STROKE_RATIO * STATUS_INK)
    return min(WEIGHTS, key=error)


def app_weight(stroke, square_height):
    """Single weight of the application icons: stroke / height of the square APP_SQUARE closest to STROKE_RATIO."""
    return min(WEIGHTS, key=lambda weight: abs(stroke(weight) / square_height(weight) - STROKE_RATIO))


# ---- stylesheets
def read_css(files):
    return '\n'.join(Path(f).read_text(encoding='utf-8') for f in files)


def shell_css():
    return read_css(sorted(SHELL_CSS_DIR.glob('*.css')))


def gtk4_css():
    return read_css(sorted(GTK4_CSS_DIR.glob('m3e-gtk4*.css')))


def rule_px(css, selector, prop):
    """Value in px of `prop` in the last rule whose selector list contains `selector` exactly (later rules win, as in
    the cascade between rules of equal specificity). Raises LookupError when no rule declares it."""
    value = None
    # Comments and matugen placeholders ({{colors.primary.default.hex}}) out of the way of the rule braces.
    css = re.sub(r'\{\{.*?\}\}', 'placeholder', re.sub(r'/\*.*?\*/', '', css, flags=re.S))
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        if selector not in (' '.join(s.split()) for s in sel.split(',')):
            continue
        for m in re.finditer(rf'(?:^|[;\s]){re.escape(prop)}\s*:\s*([\d.]+)px\s*;', body):
            value = float(m.group(1))
    if value is None:
        raise LookupError(f'no "{prop}: <n>px" in a rule for "{selector}"')
    return value


# ---- font
def font_file(family='Google Sans Flex'):
    """Font file fontconfig uses for `family`; refuses a fallback face."""
    out = subprocess.run(['fc-match', '-f', '%{family}\n%{file}', family], capture_output=True, text=True,
                         check=True).stdout.split('\n')
    if family not in out[0].split(','):
        raise LookupError(f'{family} is not installed (fontconfig falls back to {out[0]})')
    return out[1]


def cap_height(path):
    """Cap height of a font, in em (OS/2 sCapHeight / unitsPerEm)."""
    from fontTools.ttLib import TTFont    # only the checker needs fontTools
    font = TTFont(path)
    return font['OS/2'].sCapHeight / font['head'].unitsPerEm


def targets(cap, shell, gtk4):
    """Sizes of the grid: `cap` cap height in em, `shell` and `gtk4` stylesheet texts."""
    clock = rule_px(shell, *CLOCK)
    return {
        'cap_height': cap,
        'clock': clock,
        'bar_ink': cap * clock,                         # ink height of a top-bar icon = cap height of the clock
        'bar_icon': rule_px(shell, *BAR_ICON),          # icon-size set by the stylesheet
        'bar_icon_expected': cap * clock / STATUS_INK,
        'header_ink': cap * rule_px(shell, *BODY_TEXT),  # cap height of the body text, as the window buttons
        'header_icon': rule_px(gtk4, *HEADER_ICON),
    }
