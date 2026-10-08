"""Pure helpers of the Material-Symbols icon builder (no I/O): file naming, SVG path extraction, framing maths.

Coordinates are Material's 960-unit grid with the origin at the bottom-left: viewBox "0 -960 960 960".
"""
import re

SYMBOLIC_FILL = '#2e3436'          # GTK recolours symbolic icons: any opaque colour will do


def upstream_name(name, opsz=24, wght=400, fill=False):
    """File name in the Material Symbols repository: <name>[_wght<g>][fill1]_<opsz>px.svg (weight 400 and outline
    carry no suffix)."""
    tag = (f'wght{wght}' if wght != 400 else '') + ('fill1' if fill else '')
    return f'{name}{"_" + tag if tag else ""}_{opsz}px.svg'


def cache_name(variant, opsz=24, wght=400):
    """Cache file name of a symbol variant (its upstream name); a leading "!" means the filled (fill1) variant."""
    return upstream_name(variant.lstrip('!'), opsz, wght, variant.startswith('!'))


def remote_names(variant, opsz=24, wght=400):
    """File names to try on the Material Symbols repository, most specific first: a symbol without a filled
    variant falls back to its outline."""
    name = variant.lstrip('!')
    return list(dict.fromkeys([cache_name(variant, opsz, wght), upstream_name(name, opsz, wght)]))


def box_key(variant, opsz=24, wght=400):
    """Key of a measured ink box in bbox.json."""
    if (opsz, wght) == (24, 400):
        return variant
    return f'{variant}@{opsz}' if wght == 400 else f'{variant}@{opsz}@w{wght}'


def extract_paths(svg_text):
    """The <path/> elements of an SVG, recoloured for symbolic use."""
    return ''.join(re.findall(r'<path[^>]*/>', svg_text)).replace('<path ', f'<path fill="{SYMBOLIC_FILL}" ')


def underlay(paths, opacity):
    """Paths drawn in faded ink as one group, so overlapping parts do not add up."""
    return f'<g opacity="{opacity:g}">{paths}</g>'


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
