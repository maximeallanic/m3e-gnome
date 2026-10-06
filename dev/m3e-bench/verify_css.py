#!/usr/bin/env python3
"""Loads a CSS file in GTK 3 or GTK 4 and reports parsing errors (unknown property, invalid value...).

Usage: verify_css.py <m3e-gtk3.css> <m3e-gtk4.css>   (exit code 0 if there is no error)
Parses the stylesheet (and the parts it @imports, resolved next to it) in a throw-away Gtk.CssProvider (no window, no display connection beyond what importing
Gtk needs); it never touches the user's theme or settings.
"""
import subprocess
import sys

PROBE = r'''
import sys, gi
gi.require_version("Gtk", sys.argv[1])
from gi.repository import Gtk
p = Gtk.CssProvider()
def on_error(_p, section, err):
    start = section.get_start_location() if sys.argv[1] == "4.0" else None
    line = start.lines + 1 if start else section.get_start_line() + 1
    f = section.get_file()
    print(f"{f.get_basename() if f else sys.argv[2]}:{line}: {err.message}")
p.connect("parsing-error", on_error)
try:
    # From the file, not from a string: the relative @import url() of an index file resolve against its directory.
    p.load_from_path(sys.argv[2])
except Exception:
    pass
'''


def verify(path, version):
    r = subprocess.run([sys.executable, "-c", PROBE, version, str(path)], capture_output=True, text=True,
                       timeout=60)
    errors = [l for l in r.stdout.splitlines() if l.strip()]
    # A named colour (@primary) is only known with the theme: it is not a syntax error.
    return [e for e in errors if "is not defined" not in e and "not a valid color" not in e]


def main(css3, css4):
    errors = verify(css3, "3.0") + verify(css4, "4.0")
    print("\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
