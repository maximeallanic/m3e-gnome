#!/usr/bin/env python3
"""GTK 4 client of the GTK motion bench. Started by scenario.py inside the nested Shell only.

Usage: client-gtk4.py <output_dir>
The theme comes from the GTK configuration of the bench (private XDG_CONFIG_HOME: Material-Gnome + M3E overrides).
The client plays its own states (set_state_flags, scrollbar classes), without a pointer, and records frame by frame
the allocated sizes of the handles (switch, slider, scrollbar) and the radius of pressed buttons (Gtk.WidgetPaintable
capture -> pixels). Writes <output>/client4-data.json and the PNGs client4-*.png.
GTK warnings ("reported min width...") go to stderr (journal-client4.log); client4-data.json gives the CSS path of
every widget address seen, to link a warning to the faulty node. Text widgets carry Latin, CJK and Arabic samples
(samples.py): minimum widths depend on the script.
"""
import json
import math
import sys
import time

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, Graphene, Gtk

import samples

OUT = sys.argv[1]
res = {"traces": {}, "addresses": {}, "captures": [], "radii": {}, "checks": []}
app = Adw.Application(application_id="io.github.maximeallanic.M3eBenchGtk4", flags=Gio.ApplicationFlags.NON_UNIQUE)


def descendants(w):
    child = w.get_first_child()
    while child:
        yield child
        yield from descendants(child)
        child = child.get_next_sibling()


def css_node(w):
    return w.get_css_name() + "".join(f".{c}" for c in w.get_css_classes())


def css_path(w):
    parts = []
    while w is not None:
        parts.append(css_node(w))
        w = w.get_parent()
    return " > ".join(reversed(parts))


def address(w):
    r = repr(w)                                   # <... (GtkGizmo at 0x55...)>
    i = r.rfind(" at 0x")
    return r[i + 4:r.rfind(")")] if i > 0 else r


def record_addresses(root):
    for w in [root, *descendants(root)]:
        res["addresses"].setdefault(address(w), css_path(w))


def texture(widget):
    width, height = widget.get_width(), widget.get_height()
    if width <= 0 or height <= 0:
        return None
    snapshot = Gtk.Snapshot()
    Gtk.WidgetPaintable.new(widget).snapshot(snapshot, width, height)
    node = snapshot.to_node()
    if node is None:
        return None
    return widget.get_native().get_renderer().render_texture(node, Graphene.Rect().init(0, 0, width, height))


def capture(widget, name):
    t = texture(widget)
    if t:
        t.save_to_png(f"{OUT}/client4-{name}.png")
        res["captures"].append(f"client4-{name}.png")


def radius(widget):
    """Radius of the top-left corner of the widget background, from the transparent area of the corner: A = r^2 (1 - pi/4).

    Measured on the texture of the widget alone (nothing is drawn outside the corner); antialiasing counts as a fraction."""
    t = texture(widget)
    if not t:
        return None
    width, height = t.get_width(), t.get_height()
    downloader = Gdk.TextureDownloader.new(t)
    downloader.set_format(Gdk.MemoryFormat.R8G8B8A8)
    data_bytes, stride = downloader.download_bytes()
    data = data_bytes.get_data()
    side = min(width, height) // 2
    area = sum(1 - data[y * stride + x * 4 + 3] / 255 for y in range(side) for x in range(side))
    return round((area / (1 - math.pi / 4)) ** 0.5, 1)


class Recorder:
    def __init__(self, window):
        self.window = window

    def trace(self, name, read, duration_ms):
        """Values read at every frame during duration_ms."""
        series = []
        t0 = time.monotonic()

        def tick(_w, _clock):
            t = (time.monotonic() - t0) * 1000
            series.append({"t": round(t), **read()})
            if t >= duration_ms:
                res["traces"][name] = series
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE
        self.window.add_tick_callback(tick)


def build_sidebar():
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sidebar.add_css_class("sidebar")
    scrolled = Gtk.ScrolledWindow(vexpand=True)
    listbox = Gtk.ListBox()
    listbox.add_css_class("navigation-sidebar")
    for i in range(60):
        listbox.append(Gtk.Label(label=samples.cycle("Item", i), xalign=0))
    scrolled.set_child(listbox)
    sidebar.append(scrolled)
    return sidebar


def build_controls():
    """Buttons, switches, check box and radios (one script per text), then sliders and progress bar."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_start=16, margin_end=16, margin_top=16)
    row = Gtk.Box(spacing=16)
    buttons = {
        "default": Gtk.Button(label=samples.LATIN),
        "pill": Gtk.Button(label=samples.CJK),
        "icon": Gtk.Button(icon_name="edit-copy-symbolic"),
        "toggle": Gtk.ToggleButton(label=samples.ARABIC),
        "suggested": Gtk.Button(label=samples.LATIN),
    }
    buttons["pill"].add_css_class("pill")
    buttons["suggested"].add_css_class("suggested-action")
    for b in buttons.values():
        b.set_valign(Gtk.Align.CENTER)
        row.append(b)
    switches = [Gtk.Switch(valign=Gtk.Align.CENTER), Gtk.Switch(active=True, valign=Gtk.Align.CENTER)]
    for s in switches:
        row.append(s)
    radio_a = Gtk.CheckButton(label=samples.LATIN, active=True)
    radio_b = Gtk.CheckButton(label=samples.CJK, group=radio_a)
    row.append(Gtk.CheckButton(label=samples.ARABIC))
    row.append(radio_a)
    row.append(radio_b)
    box.append(row)

    sliders = []
    row2 = Gtk.Box(spacing=24)
    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, hexpand=True)
    for value, option in ((30, None), (70, "fine-tune"), (50, "marks")):
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        sc.set_value(value)
        if option == "fine-tune":
            sc.add_css_class("fine-tune")
        if option == "marks":
            for mark in (0, 25, 50, 75, 100):
                sc.add_mark(mark, Gtk.PositionType.BOTTOM, None)
        sliders.append(sc)
        column.append(sc)
    column.append(Gtk.ProgressBar(fraction=0.4))
    row2.append(column)
    vertical = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1)
    vertical.set_value(40)
    vertical.set_size_request(-1, 200)
    sliders.append(vertical)
    row2.append(vertical)
    box.append(row2)
    return box, buttons, switches, sliders


def build_scrolling_areas():
    """Vertical and horizontal scrolled areas (overlay scrollbars), like the views of Files."""
    scrolled, zone = [], Gtk.Box(spacing=16)
    for orientation in ("v", "h"):
        sw = Gtk.ScrolledWindow(hexpand=True, min_content_height=260)
        if orientation == "v":
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for i in range(200):
                content.append(Gtk.Label(label=samples.cycle("Row", i), xalign=0))
        else:
            content = Gtk.Box()
            for i in range(80):
                content.append(Gtk.Label(label=samples.cycle(" Column", i) + " "))
        sw.set_child(content)
        scrolled.append(sw)
        zone.append(sw)
    return zone, scrolled


def build_preferences():
    """Settings-page widgets (AdwPreferencesPage): switch rows off, on, disabled (one script per row), an activatable
    row, and a two-page navigation view (header back button)."""
    page = Adw.PreferencesPage(hexpand=True)
    group = Adw.PreferencesGroup(title=samples.LATIN)
    for caption, active, sensitive in ((samples.LATIN, False, True), (samples.CJK, True, True),
                                       (samples.ARABIC, True, False)):
        group.add(Adw.SwitchRow(title=caption, active=active, sensitive=sensitive))
    group.add(Adw.ActionRow(title=samples.CJK, subtitle=samples.ARABIC, activatable=True))
    page.add(group)
    page.set_size_request(420, 380)
    nav = Adw.NavigationView(hexpand=True)
    for title in ("Home", samples.CJK):
        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar())
        view.set_content(Gtk.Label(label=title))
        nav.add(Adw.NavigationPage(title=title, tag=title, child=view))
    nav.set_size_request(320, 160)
    row = Gtk.Box(spacing=16)
    row.append(page)
    row.append(nav)
    return row, page, nav


def build(app):
    win = Adw.ApplicationWindow(application=app, title="GTK motion bench (GTK 4)", default_width=1500,
                                default_height=950)
    root = Adw.ToolbarView()
    win.set_content(root)
    header = Adw.HeaderBar()
    header.pack_start(Gtk.Button(icon_name="tab-new-symbolic"))
    root.add_top_bar(header)
    view = Adw.TabView()
    tab_bar = Adw.TabBar(view=view, autohide=False)
    root.add_top_bar(tab_bar)
    win.add_css_class("has-tab-bar")

    # Content: split view (sidebar like Files / Settings) + component grid.
    split = Adw.NavigationSplitView()
    split.set_sidebar(Adw.NavigationPage(title=samples.LATIN, child=build_sidebar()))
    grid, buttons, switches, sliders = build_controls()
    zone, scrolled = build_scrolling_areas()
    grid.append(zone)
    prefs_row, prefs, nav = build_preferences()
    grid.append(prefs_row)
    split.set_content(Adw.NavigationPage(title=samples.CJK, child=grid))

    pages = []

    def add_tab(i):
        p = view.append(Gtk.Label(label=samples.cycle("page", i)))
        p.set_title(samples.cycle("tab", i))
        p.set_icon(Gio.ThemedIcon.new("utilities-terminal-symbolic"))
        pages.append(p)
        return p
    add_tab(0)
    # The pages only carry a label: the grid is outside the tab view (view hidden, bar shown).
    root.set_content(Gtk.Box(orientation=Gtk.Orientation.VERTICAL))
    root.get_content().append(split)
    split.set_vexpand(True)
    view.set_visible(False)
    root.get_content().append(view)
    win.present()
    win.m3e_prefs, win.m3e_nav = prefs, nav
    return win, view, pages, add_tab, buttons, switches, sliders, scrolled, tab_bar


def check(name, expected, measured):
    """Expectation of the bench (GTK style batch): a deviation is counted by summary.py."""
    res["checks"].append({"name": name, "expected": expected, "measured": measured, "ok": expected == measured})


def gizmos(w, css_name):
    return [d for d in descendants(w) if d.get_css_name() == css_name]


def play_tabs(win, view, pages, add_tab, tab_bar):
    """1. Tabs: opened one by one (AdwTabBox animates the width), hover, selection, closing."""
    for i in range(1, 6):
        add_tab(i)
        yield 350
        record_addresses(win)
    view.set_selected_page(pages[2])
    yield 400
    capture(tab_bar, "tabs")
    tabs = gizmos(tab_bar, "tab")
    if len(tabs) > 1:
        tabs[1].set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        yield 400
        capture(tab_bar, "tab-hovered")
        tabs[1].unset_state_flags(Gtk.StateFlags.PRELIGHT)
    for p in list(pages[3:]):
        view.close_page(p)
        yield 450
        record_addresses(win)
    add_tab(9)
    yield 450
    record_addresses(win)


def play_scrollbars(win, scrolled, recorder):
    """2. Scrollbars: scrolling (indicator), hover (full bar), press, back to the indicator."""
    for sw in scrolled + [d for d in descendants(win) if d.get_css_name() == "scrolledwindow"][:1]:
        adj = sw.get_vadjustment() if sw.get_vadjustment().get_upper() > sw.get_vadjustment().get_page_size() \
            else sw.get_hadjustment()
        adj.set_value(adj.get_upper() / 3)
        yield 300
        record_addresses(win)
        for sb in gizmos(sw, "scrollbar"):
            sb.add_css_class("hovering")
            sliders = gizmos(sb, "slider")
            yield 450
            for s in sliders:
                s.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
            yield 450
            for s in sliders:
                s.set_state_flags(Gtk.StateFlags.ACTIVE, False)
            yield 300
            for s in sliders:
                s.unset_state_flags(Gtk.StateFlags.ACTIVE | Gtk.StateFlags.PRELIGHT)
            sb.remove_css_class("hovering")
            if sliders:
                s0 = sliders[0]
                recorder.trace(f"scrollbar-return-{len(res['traces'])}",
                               lambda s0=s0: {"w": s0.get_width(), "h": s0.get_height()}, 700)
            yield 800
    capture(win, "scrolling")


def play_sliders(win, sliders, recorder):
    """3. Sliders: hover, press (thinner handle), release; animated value."""
    for sc in sliders:
        handles = gizmos(sc, "slider")
        if not handles:
            continue
        h0 = handles[0]
        recorder.trace(f"slider-{len(res['traces'])}", lambda h0=h0: {"w": h0.get_width(), "h": h0.get_height()}, 1100)
        h0.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        yield 200
        h0.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        sc.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        yield 400
        h0.unset_state_flags(Gtk.StateFlags.ACTIVE | Gtk.StateFlags.PRELIGHT)
        sc.unset_state_flags(Gtk.StateFlags.ACTIVE)
        yield 600
        sc.set_value(90)
        yield 200
    capture(win, "sliders")


def play_switches(switches, recorder):
    """4. Switches: toggle (handle size and margin), press. Icon handle (Pixel Settings): 24 dp at rest in both
    states (Switch.IconHandleWidth), 28 when pressed."""
    for s in switches:
        handle = gizmos(s, "slider")[0]
        check(f"handle {'on' if s.get_active() else 'off'} (w, h)", [24, 24], [handle.get_width(), handle.get_height()])
    for s in switches:
        handle = gizmos(s, "slider")[0]
        recorder.trace(f"switch-{len(res['traces'])}",
                       lambda handle=handle: {"w": handle.get_width(), "h": handle.get_height()}, 700)
        s.set_active(not s.get_active())
        yield 800
        s.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        yield 400
        check(f"handle pressed {len(res['checks'])} (w, h)", [28, 28], [handle.get_width(), handle.get_height()])
        s.unset_state_flags(Gtk.StateFlags.ACTIVE)
        yield 500


def play_buttons(win, buttons):
    """5. Buttons: shape morph on press (radius recorded frame by frame) then on release."""
    for name, b in buttons.items():
        series = []
        t0 = time.monotonic()

        def tick(_w, _clock, b=b, series=series, t0=t0):
            t = (time.monotonic() - t0) * 1000
            series.append({"t": round(t), "r": radius(b), "h": b.get_height()})
            return GLib.SOURCE_CONTINUE if t < 1100 else GLib.SOURCE_REMOVE
        win.add_tick_callback(tick)
        b.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        yield 550
        b.unset_state_flags(Gtk.StateFlags.ACTIVE)
        yield 650
        res["radii"][name] = series


def play_preferences(win):
    """6. Settings page and back button."""
    capture(win.m3e_prefs, "preferences")
    rows = [d for d in descendants(win.m3e_prefs) if d.get_css_name() == "row"]
    if rows:
        rows[-1].set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        yield 400
        capture(win.m3e_prefs, "preferences-hover")
        rows[-1].unset_state_flags(Gtk.StateFlags.PRELIGHT)
    win.m3e_nav.push_by_tag(samples.CJK)
    yield 900
    record_addresses(win)
    capture(win.m3e_nav, "back")
    page = win.m3e_nav.get_visible_page()
    backs = [d for d in descendants(page) if isinstance(d, Gtk.Button) and d.get_icon_name() == "go-previous-symbolic"]
    res["back"] = css_path(backs[0]) if backs else None
    if backs:
        _ok, bounds = backs[0].compute_bounds(backs[0])   # border box (get_width/height = content only)
        check("back button, circle (w, h)", [30, 30], [round(bounds.get_width()), round(bounds.get_height())])
        capture(backs[0], "back-button")
    capture(win, "final")
    record_addresses(win)


def play(app):
    win, view, pages, add_tab, buttons, switches, sliders, scrolled, tab_bar = build(app)
    recorder = Recorder(win)
    yield 1200
    record_addresses(win)
    capture(win, "initial")
    yield from play_tabs(win, view, pages, add_tab, tab_bar)
    yield from play_scrollbars(win, scrolled, recorder)
    yield from play_sliders(win, sliders, recorder)
    yield from play_switches(switches, recorder)
    yield from play_buttons(win, buttons)
    yield from play_preferences(win)
    yield 300
    with open(f"{OUT}/client4-data.json", "w", encoding="utf-8") as out:
        json.dump(res, out, ensure_ascii=False, indent=1)
    app.quit()


def start(app):
    steps = play(app)

    def advance():
        try:
            GLib.timeout_add(next(steps), advance)
        except StopIteration:
            pass
        return GLib.SOURCE_REMOVE
    advance()


app.connect("activate", start)
app.run([])
