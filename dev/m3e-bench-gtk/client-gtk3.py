#!/usr/bin/env python3
"""GTK 3 client of the GTK motion bench. Started by scenario.py inside the nested Shell only.

Usage: client-gtk3.py <output_dir>
Theme: GTK_THEME (Material-Gnome or Material-Gnome:dark, set by scenario.py) + the bench gtk-3.0/gtk.css.
Plays its states (set_state_flags, scrollbar classes) on tabs (GtkNotebook), scrollbars, sliders, switches,
check boxes, radios and buttons, and records frame by frame the animated values (GtkStyleContext.get_property:
button radius, handle size). Writes <output>/client3-data.json and the PNGs client3-*.png (icon switches and boxed
list). Text widgets carry Latin, CJK and Arabic samples (samples.py): minimum widths depend on the script.
Negative-size GTK 3 warnings ("Negative content width", "attempt to allocate ... -N") go to stderr.
"""
import json
import sys
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

import samples

OUT = sys.argv[1]
res = {"traces": {}}
win = Gtk.Window(title="GTK motion bench (GTK 3)")
win.set_default_size(1200, 800)
column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=12)
win.add(column)

notebook = Gtk.Notebook(scrollable=True)
for i in range(3):
    notebook.append_page(Gtk.Label(label=samples.cycle("page", i)), Gtk.Label(label=samples.cycle("tab", i)))
column.pack_start(notebook, False, False, 0)

row = Gtk.Box(spacing=16)
buttons = {"default": Gtk.Button(label=samples.LATIN), "suggested": Gtk.Button(label=samples.CJK),
           "icon": Gtk.Button.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.BUTTON),
           "toggle": Gtk.ToggleButton(label=samples.ARABIC)}
buttons["suggested"].get_style_context().add_class("suggested-action")
for b in buttons.values():
    b.set_valign(Gtk.Align.CENTER)
    row.pack_start(b, False, False, 0)
switches = [Gtk.Switch(valign=Gtk.Align.CENTER), Gtk.Switch(active=True, valign=Gtk.Align.CENTER)]
for s in switches:
    row.pack_start(s, False, False, 0)
radio_a = Gtk.RadioButton(label=samples.LATIN)
radio_b = Gtk.RadioButton.new_with_label_from_widget(radio_a, samples.CJK)
check = Gtk.CheckButton(label=samples.ARABIC)
for w in (check, radio_a, radio_b):
    row.pack_start(w, False, False, 0)
column.pack_start(row, False, False, 0)

# Boxed list in the style of a settings page: switch off, on, disabled; one script per row.
boxed_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
boxed_list.get_style_context().add_class("boxed-list")
for caption, active, sensitive in ((samples.LATIN, False, True), (samples.CJK, True, True),
                                   (samples.ARABIC, True, False)):
    list_row = Gtk.Box(spacing=12)
    list_row.pack_start(Gtk.Label(label=caption, xalign=0), True, True, 0)
    list_row.pack_end(Gtk.Switch(active=active, sensitive=sensitive, valign=Gtk.Align.CENTER), False, False, 0)
    boxed_list.add(list_row)
# Rendered off screen (Gtk.OffscreenWindow: capture without the cairo binding of PyGObject, absent from the system).
offscreen = Gtk.OffscreenWindow()
list_frame = Gtk.Box(margin=24)
list_frame.set_size_request(480, -1)
list_frame.pack_start(boxed_list, True, True, 0)
offscreen.add(list_frame)
offscreen.show_all()

sliders = []
for value, fine in ((30, False), (70, True)):
    sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    sc.set_value(value)
    sc.set_draw_value(False)
    if fine:
        sc.get_style_context().add_class("fine-tune")
    sliders.append(sc)
    column.pack_start(sc, False, False, 0)
vertical = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1)
vertical.set_draw_value(False)
vertical.set_size_request(-1, 160)
sliders.append(vertical)
column.pack_start(Gtk.ProgressBar(fraction=0.4), False, False, 0)

area = Gtk.Box(spacing=12)
area.pack_start(vertical, False, False, 0)
scrolled = []
for orientation in "vh":
    sw = Gtk.ScrolledWindow()
    sw.set_size_request(400, 220)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if orientation == "v" else Gtk.Orientation.HORIZONTAL)
    for i in range(150 if orientation == "v" else 60):
        box.pack_start(Gtk.Label(label=samples.cycle(" item", i) + " "), False, False, 0)
    sw.add(box)
    scrolled.append(sw)
    area.pack_start(sw, True, True, 0)
column.pack_start(area, True, True, 0)
win.show_all()


def trace(name, read, duration_ms):
    series, t0 = [], time.monotonic()

    def tick(_w, _clock):
        t = (time.monotonic() - t0) * 1000
        series.append({"t": round(t), **read()})
        if t >= duration_ms:
            res["traces"][name] = series
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE
    win.add_tick_callback(tick)


def capture(offscreen_window, name):
    pixbuf = offscreen_window.get_pixbuf()
    if pixbuf:
        pixbuf.savev(f"{OUT}/client3-{name}.png", "png", [], [])


def radius(widget):
    ctx = widget.get_style_context()
    return {"r": ctx.get_property("border-radius", ctx.get_state())}


def play():
    yield 1000
    for i in range(3, 7):                                      # tabs opened then closed
        notebook.append_page(Gtk.Label(label=samples.cycle("page", i)), Gtk.Label(label=samples.cycle("tab", i)))
        notebook.show_all()
        yield 300
    notebook.set_current_page(2)
    yield 300
    for _ in range(3):
        notebook.remove_page(-1)
        yield 300
    for sw in scrolled:                                        # scrollbars
        for adj in (sw.get_vadjustment(), sw.get_hadjustment()):
            adj.set_value((adj.get_upper() - adj.get_page_size()) / 3)
        yield 300
        for sb in (sw.get_vscrollbar(), sw.get_hscrollbar()):
            ctx = sb.get_style_context()
            ctx.add_class("hovering")
            yield 400
            sb.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
            yield 400
            sb.set_state_flags(Gtk.StateFlags.ACTIVE, False)
            yield 300
            sb.unset_state_flags(Gtk.StateFlags.ACTIVE | Gtk.StateFlags.PRELIGHT)
            ctx.remove_class("hovering")
            yield 700
    for sc in sliders:                                         # sliders: hover, press
        sc.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        yield 200
        sc.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        yield 400
        sc.unset_state_flags(Gtk.StateFlags.ACTIVE | Gtk.StateFlags.PRELIGHT)
        yield 500
    for s in switches:                                         # switches
        s.set_active(not s.get_active())
        yield 700
    for w in (check, radio_b, radio_a):                        # check box and radios
        w.set_active(not w.get_active()) if w is check else w.set_active(True)
        yield 500
    for name, b in buttons.items():                            # button shape morph
        trace(f"radius-{name}", lambda b=b: radius(b), 1000)
        b.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        yield 500
        b.unset_state_flags(Gtk.StateFlags.ACTIVE)
        yield 600
    yield 300
    capture(offscreen, "settings")
    with open(f"{OUT}/client3-data.json", "w", encoding="utf-8") as out:
        json.dump(res, out, ensure_ascii=False, indent=1)
    Gtk.main_quit()


steps = play()


def advance():
    try:
        GLib.timeout_add(next(steps), advance)
    except StopIteration:
        pass
    return GLib.SOURCE_REMOVE


advance()
Gtk.main()
