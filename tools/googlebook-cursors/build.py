#!/usr/bin/env python3
"""Build the Googlebook cursor theme (the vector cursors of desktop Android, AOSP frameworks/base, Apache 2.0)
in Xcursor format, without xcursorgen: rendered with rsvg-convert, the PNG is decoded here and converted to
premultiplied ARGB.

Usage: build.py [black|white] [--icons-dir DIR]
  -> DIR/Googlebook (black) or DIR/Googlebook-White; DIR defaults to $XDG_DATA_HOME/icons (~/.local/share/icons).
Downloads the AOSP vector drawables (pinned commit) into $XDG_CACHE_HOME/m3e-gnome/googlebook-cursors.
Requires: rsvg-convert."""
import argparse
import base64
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xcursor import A, parse_xml, render, vector_to_svg, xcursor  # noqa: E402

REV = '1cdfff555f4a21f71ccc978290e2e212e2f8b168'
SRC = f'https://android.googlesource.com/platform/frameworks/base/+/{REV}/core/res/res/drawable'
CACHE = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'm3e-gnome' / 'googlebook-cursors' / REV[:12]
SIZES = (24, 32, 48, 64, 72, 96)            # nominal sizes; 24 dp in Android = size 24
# AOSP styles (values/styles.xml): PointerIconVectorStyleFillBlack + StrokeWhite by default
STYLES = {'black': {'Fill': '#000', 'FillInverse': '#FFF', 'Stroke': '#FFF', 'StrokeInverse': '#000'},
          'white': {'Fill': '#FFF', 'FillInverse': '#000', 'Stroke': '#000', 'StrokeInverse': '#FFF'}}
THEME_NAMES = {'black': 'Googlebook', 'white': 'Googlebook-White'}

# AOSP name -> CSS / X11 cursor names (the first is the file, the others are links)
NAMES = {
    'arrow': ['default', 'left_ptr', 'arrow', 'top_left_arrow', 'right_ptr', 'center_ptr'],
    'hand': ['pointer', 'hand2', 'hand1', 'hand', 'pointing_hand'],
    'text': ['text', 'xterm', 'ibeam'],
    'vertical_text': ['vertical-text'],
    'wait': ['wait', 'watch', 'progress', 'left_ptr_watch', 'half-busy'],
    'crosshair': ['crosshair', 'cross', 'tcross', 'cross_reverse', 'diamond_cross'],
    'cell': ['cell', 'plus'],
    'help': ['help', 'question_arrow', 'whats_this', 'left_ptr_help', 'dnd-ask'],
    'context_menu': ['context-menu'],
    'copy': ['copy', 'dnd-copy'],
    'alias': ['alias', 'link', 'dnd-link'],
    'nodrop': ['not-allowed', 'no-drop', 'dnd-no-drop', 'crossed_circle', 'forbidden', 'circle'],
    'grab': ['grab', 'openhand', 'dnd-none'],
    'grabbing': ['grabbing', 'closedhand', 'dnd-move'],
    'all_scroll': ['all-scroll', 'move', 'fleur', 'size_all', 'all-resize'],
    'horizontal_double_arrow': ['ew-resize', 'col-resize', 'e-resize', 'w-resize', 'h_double_arrow',
                                'sb_h_double_arrow', 'size_hor', 'left_side', 'right_side', 'split_h'],
    'vertical_double_arrow': ['ns-resize', 'row-resize', 'n-resize', 's-resize', 'v_double_arrow',
                              'sb_v_double_arrow', 'size_ver', 'top_side', 'bottom_side', 'split_v'],
    'top_left_diagonal_double_arrow': ['nwse-resize', 'nw-resize', 'se-resize', 'size_fdiag', 'bd_double_arrow',
                                       'top_left_corner', 'bottom_right_corner'],
    'top_right_diagonal_double_arrow': ['nesw-resize', 'ne-resize', 'sw-resize', 'size_bdiag', 'fd_double_arrow',
                                        'top_right_corner', 'bottom_left_corner'],
    'zoom_in': ['zoom-in'],
    'zoom_out': ['zoom-out'],
    'handwriting': ['pencil', 'draft'],
}


def fetch(name, attempts=5):
    """Cached AOSP drawable as an XML root. gitiles rate-limits (HTTP 429): wait and retry only for that."""
    out = CACHE / f'{name}.xml'
    if not out.exists():
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(f'{SRC}/{name}.xml?format=TEXT', timeout=30) as r:
                    data = base64.b64decode(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == attempts - 1:
                    raise
                time.sleep(2 ** attempt)
        tmp = out.with_suffix('.part')
        tmp.write_bytes(data)
        tmp.replace(out)
    return parse_xml(out)


def build(style, icons_dir):
    theme = THEME_NAMES[style]
    dest = icons_dir / theme
    CACHE.mkdir(parents=True, exist_ok=True)
    (dest / 'cursors').mkdir(parents=True, exist_ok=True)
    for f in (dest / 'cursors').iterdir():
        f.unlink()
    for aosp, names in NAMES.items():
        icon = fetch(f'pointer_{aosp}_vector_icon')
        hx, hy = (float(icon.get(A + k).rstrip('dp')) for k in ('hotSpotX', 'hotSpotY'))
        root = fetch(f'pointer_{aosp}_vector')
        if root.tag == 'animation-list':
            frames = [(fetch(i.get(A + 'drawable').split('/')[-1]), int(i.get(A + 'duration'))) for i in root]
            frames = [(frames[k][0], 2 * frames[k][1]) for k in range(0, len(frames), 2)]   # 44 frames at 32 ms
        else:
            frames = [(root, 0)]
        images = []
        for t in SIZES:
            for vec, delay in frames:
                images.append((t, t, round(hx * t / 24), round(hy * t / 24), delay,
                               render(vector_to_svg(vec, STYLES[style]), t)))
        (dest / 'cursors' / names[0]).write_bytes(xcursor(images))
        for alias in names[1:]:
            (dest / 'cursors' / alias).symlink_to(names[0])
    (dest / 'index.theme').write_text(
        f'[Icon Theme]\nName={theme}\nComment=Desktop Android / Googlebook cursors (AOSP {REV[:12]}, Apache 2.0)\n',
        encoding='utf-8')
    (dest / 'cursor.theme').write_text(f'[Icon Theme]\nName={theme}\nInherits={theme}\n', encoding='utf-8')
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('style', nargs='?', choices=sorted(STYLES), default='black')
    data_home = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    ap.add_argument('--icons-dir', type=Path, default=data_home / 'icons')
    args = ap.parse_args()
    print(build(args.style, args.icons_dir))


if __name__ == '__main__':
    main()
