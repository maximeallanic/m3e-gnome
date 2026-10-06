"""Toolkit selection of a bench process: `select()` pins the GI versions once, before widgets.py or bench.py import
Gtk. One process runs one toolkit: gtk3 (GTK 3), gtk4 (GTK 4) or adw (GTK 4 + libadwaita)."""
import gi

TK = None
GTK3 = False


def select(toolkit):
    """Pin Gtk/Gdk (and Adw for "adw") to the versions of `toolkit`; must run before the first Gtk import."""
    global TK, GTK3
    if toolkit not in ("gtk3", "gtk4", "adw"):
        raise ValueError(f"unknown toolkit: {toolkit}")
    TK, GTK3 = toolkit, toolkit == "gtk3"
    gi.require_version("Gtk", "3.0" if GTK3 else "4.0")
    gi.require_version("Gdk", "3.0" if GTK3 else "4.0")
    if toolkit == "adw":
        gi.require_version("Adw", "1")
