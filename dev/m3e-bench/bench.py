#!/usr/bin/env python3
"""Bench: grid of widgets x states, full screen, in one toolkit.

SAFETY: this program opens a full-screen GTK window and forces widget states. It must ONLY run inside an isolated,
headless session: the nested GNOME Shell started by nested.sh (named Wayland socket m3e-bench-<pid>, private
XDG_RUNTIME_DIR and bus). It refuses to start anywhere else (see isolation.py): never run it by hand in a real
session.

Usage: bench.py --toolkit gtk3|gtk4|adw --batch N --out <folder> [--page P --rows a,b] [--screen C] [--quit]
Writes <out>/layout-<name>.json then <out>/ready-<name>, <name> = <toolkit>-b<N>-p<P>.
Rows that do not fit on the screen are hidden and listed in "remaining" (next page).
Modules: grid.py (rows, expected values), widgets.py (builders), paging.py (layout and paging), toolkit.py.
"""
import argparse
import json
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid  # noqa: E402
import isolation  # noqa: E402
import paging  # noqa: E402
import toolkit  # noqa: E402


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--toolkit", required=True, choices=sorted(grid.TOOLKITS))
    p.add_argument("--batch", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--page", type=int, default=0, help="page number (file names)")
    p.add_argument("--rows", help="ids of the rows to place, comma separated (the witness is always placed)")
    p.add_argument("--screen", help="connector of the screen where to open the bench")
    p.add_argument("--quit", action="store_true", help="quit once the layout is written")
    return p.parse_args(argv)


ARGS = None
CODE = 0
APP = None
DEFERRED_DIALOG = []


def apply_state(target, state):
    F = Gtk.StateFlags
    if state == "hover":
        target.set_state_flags(F.PRELIGHT, False)
    elif state == "pressed":
        target.set_state_flags(F.ACTIVE, False)
    elif state == "focus":
        target.set_state_flags(F.FOCUSED if GTK3 else F.FOCUSED | F.FOCUS_VISIBLE, False)
    elif state == "disabled":
        target.set_sensitive(False)
    elif state == "active":
        if isinstance(target, Gtk.ListBoxRow) and target.get_parent() is not None:
            parent = target.get_parent()
            if isinstance(parent, Gtk.ListBox):
                parent.select_row(target)
        if hasattr(target, "set_active") and not isinstance(target, Gtk.ComboBox if GTK3 else Gtk.DropDown):
            target.set_active(True)
        else:
            target.set_state_flags(F.CHECKED | F.SELECTED, False)


# --- window ------------------------------------------------------------------------------------------------------

def bounds(target, window):
    if GTK3:
        r = target.translate_coordinates(window, 0, 0)
        if r is None:
            raise RuntimeError(f"bounds not found for {target.get_name()} (visible={target.get_visible()}, "
                               f"realized={target.get_realized()})")
        x, y = r
        a = target.get_allocation()
        return x, y, a.width, a.height
    ok, r = target.compute_bounds(window)
    if not ok:
        raise RuntimeError(f"bounds not found for {target}")
    return r.get_x(), r.get_y(), r.get_width(), r.get_height()


def window_size(window):
    return (window.get_allocated_width(), window.get_allocated_height()) if GTK3 else \
        (window.get_width(), window.get_height())


def build(window):
    widgets.scaffold_css()
    rows, deferred = paging.select_rows(TK, ARGS.batch, ARGS.rows.split(",") if ARGS.rows else None)
    DEFERRED_DIALOG[:] = deferred
    # One FlowBox per row: the states wrap if the widget is wide. All in a scrolled window without a bar: the
    # full-screen window does not grow, the extra rows are hidden (see `ready`, fit_rows).
    g = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    for m in ("set_margin_top", "set_margin_bottom", "set_margin_start", "set_margin_end"):
        getattr(g, m)(16)
    targets, flowboxes = [], []
    for r in rows:
        flowbox = Gtk.FlowBox()
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_max_children_per_line(len(r.states))
        flowbox.set_column_spacing(8)
        flowbox.set_row_spacing(8)
        flowbox.set_homogeneous(False)
        if GTK3:
            flowbox.set_valign(Gtk.Align.START)
        widgets.append(g, flowbox)
        flowboxes.append((r.id, flowbox))
        for state in r.states:
            w, get_target = widgets.BUILDERS[r.id]()
            w.set_halign(Gtk.Align.CENTER)
            w.set_valign(Gtk.Align.CENTER)
            cell = Gtk.Box()
            cell.set_size_request(*paging.CELL)
            w.set_hexpand(True)
            widgets.append(cell, w)
            if GTK3:
                flowbox.add(cell)
            else:
                flowbox.append(cell)
            targets.append((r.id, state, w, get_target))
    scroller = Gtk.ScrolledWindow()
    scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
    if GTK3:
        scroller.add(g)
        sensor = Gtk.EventBox()
        sensor.set_above_child(True)
        sensor.set_visible_window(False)
        sensor.add(scroller)
        window.add(sensor)
    elif TK == "adw":
        scroller.set_child(g)
        window.set_content(scroller)
    else:
        scroller.set_child(g)
        window.set_child(scroller)
    return targets, flowboxes


def ignore_pointer(window):
    """The real pointer must reach no widget (it would force a hover).
    GTK 4: content not targetable. GTK 3: EventBox above the content (see `build`)."""
    if not GTK3:
        (window.get_content() if TK == "adw" else window.get_child()).set_can_target(False)


def logical_screen(window):
    d = Gdk.Display.get_default()
    m = d.get_monitor_at_window(window.get_window()) if GTK3 else d.get_monitor_at_surface(window.get_surface())
    g = m.get_geometry()
    return [g.width, g.height]


def connector(window):
    if GTK3:
        screen = Gdk.Screen.get_default()
        return screen.get_monitor_plug_name(screen.get_monitor_at_window(window.get_window()))
    return Gdk.Display.get_default().get_monitor_at_surface(window.get_surface()).get_connector()


def fullscreen(window):
    """Full screen on --screen if given, otherwise on the default screen."""
    if ARGS.screen:
        if GTK3:
            screen = Gdk.Screen.get_default()
            for i in range(screen.get_n_monitors()):
                if screen.get_monitor_plug_name(i) == ARGS.screen:
                    window.fullscreen_on_monitor(screen, i)
                    return
        else:
            monitors = Gdk.Display.get_default().get_monitors()
            for i in range(monitors.get_n_items()):
                m = monitors.get_item(i)
                if m.get_connector() == ARGS.screen:
                    window.fullscreen_on_monitor(m)
                    return
        sys.exit(f"screen not found: {ARGS.screen}")
    window.fullscreen()


def fail(ex):
    global CODE
    print(f"error: {ex!r}", file=sys.stderr)
    CODE = 1
    quit_bench()
    return False


def ready(window, targets, flowboxes):
    """Screen checked -> states applied (GTK 3 recreates the title buttons after showing) -> extra rows hidden ->
    layout written."""
    if GTK3:
        window.set_focus_visible(True)
    resolved, remaining, attempts = [], [], [0]
    name = paging.page_name(TK, ARGS.batch, ARGS.page)

    def check_screen():
        ignore_pointer(window)  # early: the pointer leaving would remove a forced hover afterwards
        if ARGS.screen and connector(window) != ARGS.screen:
            attempts[0] += 1
            if attempts[0] > 6:
                return fail(RuntimeError(f"the window stays on {connector(window)}, not on {ARGS.screen}"))
            fullscreen(window)
            GLib.timeout_add(700, check_screen)
            return False
        GLib.timeout_add(300, states)
        return False

    def states():
        try:
            for rid, state, w, get_target in targets:
                t = get_target()
                if t is None:
                    raise RuntimeError(f"target not found: {rid}")
                apply_state(t, state)
                resolved.append((rid, state, t))
                if hasattr(t, "_open"):
                    t._open()
        except Exception as ex:
            return fail(ex)
        GLib.timeout_add(800, sort)
        return False

    def sort():
        try:
            for rid, state, t in resolved:  # reapplied: a late pointer event may have removed one
                if state != "disabled" and rid not in paging.ZONES:
                    apply_state(t, state)
            height = window_size(window)[1]
            remaining[:] = paging.fit_rows([(rid, bounds(fb, window)[1], bounds(fb, window)[3])
                                            for rid, fb in flowboxes], height)
            for rid, fb in flowboxes:
                if rid in remaining:
                    fb.set_visible(False)
        except Exception as ex:
            return fail(ex)
        GLib.timeout_add(500, write)
        return False

    def write():
        try:
            return _write()
        except Exception as ex:  # an error in a GLib callback must not leave the window open
            return fail(ex)

    def _write():
        size = window_size(window)
        cells = [paging.cell_record(rid, state, bounds(t, window), size)
                 for rid, state, t in resolved if rid not in remaining]
        out = Path(ARGS.out)
        out.mkdir(parents=True, exist_ok=True)
        doc = paging.layout_document(TK, ARGS.batch, ARGS.page, size, connector(window), logical_screen(window),
                                     remaining + DEFERRED_DIALOG, cells)
        (out / f"layout-{name}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        (out / f"ready-{name}").write_text("")
        if ARGS.quit:
            quit_bench()
        return False
    GLib.timeout_add(500, check_screen)


def quit_bench(*_):
    if GTK3:
        Gtk.main_quit()
    else:
        APP.quit()
    return False


def main(argv):
    global ARGS, TK, GTK3, APP, Gtk, Gdk, GLib, GLibUnix, widgets
    problem = isolation.check_isolated(os.environ)
    if problem:
        print(f"bench.py refused: {problem}", file=sys.stderr)
        return 2
    ARGS = parse_args(argv)
    toolkit.select(ARGS.toolkit)
    TK, GTK3 = toolkit.TK, toolkit.GTK3
    import widgets  # noqa: E402  (needs the pinned GTK version)
    from gi.repository import Gdk, GLib, GLibUnix, Gtk  # noqa: E402
    if TK == "adw":
        from gi.repository import Adw  # noqa: E402
    if GTK3:
        # Grayscale smoothing in the bench only: sub-pixel smoothing (system setting, applied by GTK 3 alone)
        # colours the edge of the letters and skews the measurement of the text colour.
        Gtk.Settings.get_default().set_property("gtk-xft-rgba", "none")
        f = Gtk.Window(title="m3e-bench")
        targets, flowboxes = build(f)
        f.connect("destroy", Gtk.main_quit)
        fullscreen(f)
        f.show_all()
        ready(f, targets, flowboxes)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_bench)
        Gtk.main()
        return CODE
    APP = (Adw.Application if TK == "adw" else Gtk.Application)(application_id=f"io.github.maximeallanic.M3eBench.{TK}")

    def activate(app):
        f = (Adw.ApplicationWindow if TK == "adw" else Gtk.ApplicationWindow)(application=app, title="m3e-bench")
        targets, flowboxes = build(f)
        fullscreen(f)
        f.present()
        ready(f, targets, flowboxes)
    APP.connect("activate", activate)
    GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_bench)
    r = APP.run([])
    return CODE or r


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
