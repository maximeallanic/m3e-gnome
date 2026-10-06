#!/usr/bin/env python3
"""Build the Material-Symbols icon theme: top-bar status icons (map.py) and symbolic application icons
(map_apps.py). Missing symbols are downloaded from a pinned commit of google/material-design-icons; the top-bar
ones are framed on a common ink height. The window buttons (symbolic/actions/window-*) are drawn by hand and kept.

Usage: build.py [--icons-dir DIR]
  DIR defaults to $XDG_DATA_HOME/icons (~/.local/share/icons); Material-Symbols is written to DIR/Material-Symbols
  and needs Papirus-Dark in DIR (its coloured folders are linked in).
Environment: MS_STYLE (rounded|outlined|sharp, default rounded), MS_FILL (1 = filled app icons, default),
  MS_INK_HEIGHT (share of the frame taken by status-icon ink, default 0.72), APP_INSET (default 110),
  XDG_CACHE_HOME (download cache).
Requires: rsvg-convert, ffmpeg.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import map as status_map          # noqa: E402  (local module, shadows the builtin only inside this tool)
import map_apps                   # noqa: E402
import symbols as sym             # noqa: E402

REV = 'bd8cb85bd4bad964fe6918f79665bb40c3a8efef'      # google/material-design-icons, pinned
# Material Symbols style: rounded, like Android 17 SystemUI. Try outlined or sharp with MS_STYLE.
STYLE = os.environ.get('MS_STYLE', 'rounded')
# Application icons filled (fill1) when that variant exists, like the tiles and status bar of a Pixel;
# MS_FILL=0 gives outlines (map_apps.py then keeps its per-icon "!").
FILL = os.environ.get('MS_FILL', '1') == '1'
SUFFIX = '' if STYLE == 'rounded' else f'-{STYLE}'
# Common top-bar grid, like the Android 17 status bar: all icons at the same ink height, free width.
INK_HEIGHT = float(os.environ.get('MS_INK_HEIGHT', '0.72'))
# Application icons: symbols at optical size 20, no per-icon cropping, so the Material grid keeps its proportions
# from one symbol to the next, as in Android. The frame is tightened by APP_INSET (960-grid units) to approach the
# footprint of Adwaita icons.
APP_OPSZ, APP_INSET = 20, int(os.environ.get('APP_INSET', '110'))
CACHE = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'm3e-gnome' / 'material-symbols' / f'svg{SUFFIX}'
BBOX_FILE = HERE / f'bbox{SUFFIX}.json'      # measured ink boxes, committed (rounded = bbox.json)
CTX = dict(actions='Actions', apps='Applications', categories='Categories', devices='Devices', emotes='Emotes',
           mimetypes='MimeTypes', places='Places', status='Status', ui='UI')


def fetch(variant, opsz=24):
    """Download a symbol into the cache (atomically); False if the repository does not have it."""
    out = CACHE / sym.cache_name(variant, opsz)
    if out.exists():
        return True
    name = variant.lstrip('!')
    base = f'https://raw.githubusercontent.com/google/material-design-icons/{REV}/symbols/web/{name}/materialsymbols{STYLE}/'
    for remote in sym.remote_names(variant, opsz):
        try:
            with urllib.request.urlopen(base + remote, timeout=30) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        if not data.lstrip().startswith(b'<svg'):
            raise RuntimeError(f'{base + remote}: not an SVG')
        tmp = out.with_suffix('.part')
        tmp.write_bytes(data)
        tmp.replace(out)
        return True
    return False


def measure_bbox(svg_file):
    """Ink box [x, y, w, h] of an SVG in grid units, measured on a 480 px render (2 grid units per pixel)."""
    size = 480
    render = subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), str(svg_file)],
                            capture_output=True, check=True).stdout
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', '-', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                          '-vf', 'alphaextract', '-'], input=render, capture_output=True, check=True).stdout
    rows = [raw[i * size:(i + 1) * size] for i in range(size)]
    inked = [i for i, r in enumerate(rows) if max(r) > 32]
    if not inked:
        raise RuntimeError(f'{svg_file}: empty image')
    y0, y1 = inked[0], inked[-1]
    cols = [max(rows[y][x] for y in range(y0, y1 + 1, 2)) for x in range(size)]
    inked_x = [i for i, c in enumerate(cols) if c > 32]
    x0, x1 = inked_x[0], inked_x[-1]
    return [x0 * 2, -960 + y0 * 2, (x1 - x0 + 1) * 2, (y1 - y0 + 1) * 2]


def read_symbol(variant, opsz=24):
    return (CACHE / sym.cache_name(variant, opsz)).read_text(encoding='utf-8')


def build_status(root, boxes):
    """Top-bar icons (map.py) -> root/status. Returns the missing symbols."""
    M = status_map.M
    missing = [v for v in sorted(set(M.values())) if not fetch(v)]
    # Underlay symbols (the complete Wi-Fi / cellular glyph) are fetched too
    under = {v: b for v, b in status_map.UNDERLAY.items() if v not in missing}
    for b in set(under.values()):
        if not fetch(b):
            missing.append(b)
    for v in sorted(set(M.values())):
        if v not in missing and v not in boxes:
            boxes[v] = measure_bbox(CACHE / sym.cache_name(v))
    out_dir = root / 'symbolic' / 'status'
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, v in M.items():
        if v in missing:
            continue
        paths = sym.extract_paths(read_symbol(v))
        if v in under and under[v] not in missing:
            paths = sym.extract_paths(read_symbol(under[v]), status_map.UNDERLAY_OPACITY) + paths
        if v.lstrip('!') in sym.NAV:
            viewbox, ink_width = '0 -960 960 960', None
        else:
            ref = '!battery_android_full' if v.startswith('!battery_android') else status_map.FAMILY.get(v, v)
            viewbox, ink_width = sym.status_viewbox(boxes[ref], INK_HEIGHT)
        (out_dir / f'{name}.svg').write_text(sym.status_svg(viewbox, paths, ink_width), encoding='utf-8')
    print(f'top bar: {len(M)} GNOME icons, {len(set(M.values()))} symbols, missing: {missing}')
    return missing


def app_variant(ms):
    v = ms.lstrip('^%')
    return '!' + v if FILL and not v.startswith('!') else v


def build_apps(root, boxes):
    A = {g: cv for g, cv in map_apps.A.items() if g not in status_map.M}
    missing = sorted({ms for _, ms in A.values() if not fetch(app_variant(ms), APP_OPSZ)})
    for v in sorted({app_variant(ms) for _, ms in A.values() if ms not in missing}):
        key = f'{v}@{APP_OPSZ}'
        if key not in boxes:
            boxes[key] = measure_bbox(CACHE / sym.cache_name(v, APP_OPSZ))
    for g, (ctx, ms) in A.items():
        if ms in missing:
            continue
        v = app_variant(ms)
        paths = sym.transform_app_paths(sym.extract_paths(read_symbol(v, APP_OPSZ)), ms)
        viewbox = sym.app_viewbox(boxes[f'{v}@{APP_OPSZ}'], APP_INSET, map_apps.SCALE.get(g, 1))
        (root / 'symbolic' / ctx).mkdir(parents=True, exist_ok=True)
        (root / 'symbolic' / ctx / f'{g}.svg').write_text(sym.status_svg(viewbox, paths), encoding='utf-8')
    print(f'applications: {len(A)} GNOME icons, {len({ms for _, ms in A.values()})} symbols, missing: {missing}')
    return missing


def link_papirus(icons_dir, theme_dir, symbolic_dir):
    """Link the coloured size directories of Papirus-Dark into the theme and write index.theme.

    GTK 4 walks the themes one by one and, in each, all the requested names: for a folder, Nautilus asks for
    "folder-documents", "folder", then "folder-documents-symbolic". If Material-Symbols only provided the symbolic
    version, it would come before the coloured folder inherited from Papirus. So the size directories of
    Papirus-Dark are linked (its "symbolic" directories are not declared, they stay ignored).
    Neither Papirus-Dark nor Papirus is inherited: their coloured folders are already linked here, and inheriting
    them made GTK index ~170,000 icons at each app start (~1 s). The symbolic fallback comes from Papirus-Symbolic
    (tools/papirus-symbolic.py), which links only the symbolic directories of Papirus."""
    pap = icons_dir / 'Papirus-Dark'
    index = pap / 'index.theme'
    if not index.is_file():
        sys.exit(f'build.py: {index} not found: install Papirus-Dark in {icons_dir} first')
    idx = index.read_text(encoding='utf-8')
    sections = {m.group(1): m.group(2).strip()
                for m in re.finditer(r'^\[([^\]]+)\]\n(.*?)(?=^\[|\Z)', idx, re.S | re.M)}
    pdirs = [d for d in re.search(r'^Directories=(.*)$', idx, re.M).group(1).split(',') if d and 'symbolic' not in d]
    for top in sorted({d.split('/')[0] for d in pdirs}):
        link = theme_dir / top
        if link.is_symlink():
            link.unlink()
        link.symlink_to(f'../Papirus-Dark/{top}')
    ours = sorted(d.name for d in symbolic_dir.iterdir() if d.is_dir())
    out = ['[Icon Theme]', 'Name=Material-Symbols',
           f'Comment=Material Symbols {STYLE}{" filled" if FILL else ""} symbolic icons (top bar, windows, applications) '
           'plus the coloured icons of Papirus-Dark',
           'Inherits=Papirus-Symbolic,Adwaita,hicolor',
           'Directories=' + ','.join([f'symbolic/{d}' for d in ours] + pdirs), '']
    for d in ours:
        out += [f'[symbolic/{d}]', f'Context={CTX.get(d, d)}', 'Size=16', 'MinSize=8', 'MaxSize=512', 'Type=Scalable', '']
    for d in pdirs:
        out += [f'[{d}]', sections[d], '']
    (theme_dir / 'index.theme').write_text('\n'.join(out), encoding='utf-8')
    print(f'Papirus-Dark: {len(pdirs)} coloured directories linked')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    data_home = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    ap.add_argument('--icons-dir', type=Path, default=data_home / 'icons')
    icons_dir = ap.parse_args().icons_dir
    theme = icons_dir / 'Material-Symbols'
    root = theme / 'symbolic'
    CACHE.mkdir(parents=True, exist_ok=True)
    # Regenerated icons only: the hand-drawn window buttons stay.
    for f in glob.glob(str(root / '*' / '*.svg')):
        if not os.path.basename(f).startswith('window-'):
            os.remove(f)
    boxes = json.loads(BBOX_FILE.read_text()) if BBOX_FILE.exists() else {}
    build_status(theme, boxes)
    build_apps(theme, boxes)
    BBOX_FILE.write_text(json.dumps(boxes), encoding='utf-8')
    link_papirus(icons_dir, theme, root)
    subprocess.run([sys.executable, str(HERE.parent / 'papirus-symbolic.py'), str(icons_dir)], check=True)


if __name__ == '__main__':
    main()
