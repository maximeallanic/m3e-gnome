#!/usr/bin/env python3
"""Create the Papirus-Symbolic icon theme: only the symbolic directories of Papirus, linked, without its coloured
icons. Material-Symbols inherits from it instead of the whole of Papirus.

Why: GTK 4 indexes every icon of every theme in the chain at each app start. Material-Symbols already links all the
coloured folders of Papirus-Dark; inheriting from Papirus-Dark and Papirus as well made GTK index ~170,000 icons,
about 1 s more before the window shows (measured: gnome-calculator 1.55 s -> 0.49 s). The symbolic icons of Papirus
stay the fallback of Material-Symbols (without them, ~720 icons such as audio-volume-headphones-symbolic would be
missing).

Usage: papirus-symbolic.py [icons directory, default $XDG_DATA_HOME/icons ]
Requires Papirus in that directory. gtk-update-icon-cache (or gtk4-update-icon-cache) is optional: without it the
theme is complete but has no icon cache, so GTK scans the directories at start (slower); a message says so."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_index(text):
    """({section: body}, {key: [directories]}) of an icon theme index; only symbolic directories are kept."""
    sections = {m.group(1): m.group(2).strip()
                for m in re.finditer(r'^\[([^\]]+)\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M)}

    def symbolic(key):
        m = re.search(rf'^{key}=(.*)$', text, re.M)
        return [d for d in (m.group(1).split(',') if m else []) if 'symbolic' in d]
    return sections, symbolic('Directories'), symbolic('ScaledDirectories')


def build_index(sections, dirs, scaled):
    out = ['[Icon Theme]', 'Name=Papirus-Symbolic', 'Comment=Symbolic icons of Papirus only (fallback of Material-Symbols)',
           'Inherits=hicolor', 'Directories=' + ','.join(dirs), 'ScaledDirectories=' + ','.join(scaled), '']
    for d in dirs + scaled:
        out += [f'[{d}]', sections[d], '']
    return '\n'.join(out)


def refresh_cache(theme_dir):
    """Build the icon cache of a theme directory. Returns False (after saying so) when no cache tool is installed;
    a cache tool that fails is a real error and raises."""
    tool = shutil.which('gtk-update-icon-cache') or shutil.which('gtk4-update-icon-cache')
    if not tool:
        print(f'papirus-symbolic: gtk-update-icon-cache not found: {theme_dir} has no icon cache (GTK starts slower '
              'until you install it, e.g. libgtk-3-bin / gtk-update-icon-cache / gtk3, and rerun)', file=sys.stderr)
        return False
    subprocess.run([tool, '-q', '-f', str(theme_dir)], check=True)
    return True


def main(argv):
    data_home = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    icons = Path(argv[1]) if len(argv) > 1 else data_home / 'icons'
    pap, out = icons / 'Papirus', icons / 'Papirus-Symbolic'
    index = pap / 'index.theme'
    if not index.is_file():
        print(f'papirus-symbolic: {index} not found (install Papirus first)', file=sys.stderr)
        return 1
    sections, dirs, scaled = parse_index(index.read_text(encoding='utf-8'))
    shutil.rmtree(out, ignore_errors=True)
    for d in dirs + scaled:
        top, sub = d.split('/')[:2]                    # 16x16/symbolic/actions: link 16x16/symbolic
        (out / top).mkdir(parents=True, exist_ok=True)
        link = out / top / sub
        if not link.is_symlink():
            link.symlink_to(f'../../Papirus/{top}/{sub}')
    (out / 'index.theme').write_text(build_index(sections, dirs, scaled), encoding='utf-8')
    refresh_cache(out)
    print(f'Papirus-Symbolic: {len(dirs)} + {len(scaled)} symbolic directories linked')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
