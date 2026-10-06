"""Pure helpers of the Material-Symbols icon builder (no I/O): file naming, SVG path extraction, framing maths.

Coordinates are Material's 960-unit grid with the origin at the bottom-left: viewBox "0 -960 960 960".
"""
import re

SYMBOLIC_FILL = '#2e3436'          # GTK recolours symbolic icons: any opaque colour will do
NAV = ('chevron_right', 'chevron_left')       # navigation signs keep their original size


def cache_name(variant, opsz=24):
    """Cache file name of a symbol variant; a leading "!" means the filled (fill1) variant."""
    name = variant.lstrip('!')
    fill = '_fill1' if variant.startswith('!') else ''
    size = '' if opsz == 24 else f'_{opsz}px'
    return f'{name}{fill}{size}.svg'


def remote_names(variant, opsz=24):
    """File names to try on the Material Symbols repository, most specific first."""
    name = variant.lstrip('!')
    return ([f'{name}_fill1_{opsz}px.svg'] if variant.startswith('!') else []) + [f'{name}_{opsz}px.svg']


def extract_paths(svg_text, opacity=None):
    """The <path/> elements of an SVG, recoloured for symbolic use (optionally with a fill opacity)."""
    attrs = f'fill="{SYMBOLIC_FILL}"' + (f' fill-opacity="{opacity:g}"' if opacity is not None else '')
    return ''.join(re.findall(r'<path[^>]*/>', svg_text)).replace('<path ', f'<path {attrs} ')


def status_viewbox(bbox, ink_height):
    """Square viewBox that frames `bbox` ([x, y, w, h]) so its ink takes `ink_height` of the frame height.
    A symbol wider than the frame is shrunk just enough to fit. Returns (viewBox string, ink width / side)."""
    x, y, w, h = bbox
    side = max(h / ink_height, w)
    cx, cy = x + w / 2, y + h / 2
    return f'{cx - side / 2:.1f} {cy - side / 2:.1f} {side:.1f} {side:.1f}', w / side


def app_viewbox(bbox, inset, scale=1):
    """viewBox of an application icon: the grid tightened by `inset`, widened (symmetrically around the centre)
    just enough to contain a wider symbol; overflows under 20 units (about 0.4 px at 16 px: the smoothed edge of
    circles and folders) are tolerated to keep a common footprint. `scale` < 1 shrinks the glyph."""
    x, y, w, h = bbox
    half = max(480 - x, x + w - 480, y + 960 - 480, 480 - (y + 960 + h))
    if half <= 480 - inset + 20:
        half = 480 - inset
    half /= scale
    return f'{480 - half:g} {-480 - half:g} {2 * half:g} {2 * half:g}'


def status_svg(viewbox, paths, ink_width=None):
    # data-ink-width: ink width (share of the frame) read by the status-bar extension: a St icon is square, and
    # the bar gives it back its real width so spacing between icons does not depend on the glyph shape.
    extra = f' data-ink-width="{ink_width:.3f}"' if ink_width is not None else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="{viewbox}"{extra}>{paths}</svg>\n'


def transform_app_paths(paths, marker):
    """Apply an app-icon marker prefix: "^" flips vertically, "%" rotates a quarter turn."""
    if marker.startswith('^'):
        return f'<g transform="matrix(1 0 0 -1 0 -960)">{paths}</g>'
    if marker.startswith('%'):
        return f'<g transform="rotate(90 480 -480)">{paths}</g>'
    return paths
