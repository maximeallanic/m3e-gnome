"""Widget builders of the bench: one per row id of grid.py. Import only after `toolkit.select()` (it needs the GTK
version pinned); every builder returns (widget placed in the cell, function returning the target to measure)."""
import toolkit
from gi.repository import Gdk, Gio, GLib, Gtk

TK = toolkit.TK
GTK3 = toolkit.GTK3
if TK == "adw":
    from gi.repository import Adw

ICON = "edit-copy-symbolic"


class Tooltip(Gtk.Box):
    """Box whose CSS node is called "tooltip": a real tooltip does not show on demand."""
    __gtype_name__ = "M3eBenchTooltip"


Tooltip.set_css_name("tooltip")


# --- helpers independent of the GTK version ----------------------------------------------------------------------

def children(w):
    if GTK3:
        out = []
        if isinstance(w, Gtk.Container):
            w.forall(out.append)
        return out
    out, c = [], w.get_first_child()
    while c is not None:
        out.append(c)
        c = c.get_next_sibling()
    return out


def find(w, test):
    """First descendant (depth first) that satisfies `test`."""
    for c in children(w):
        if test(c):
            return c
        r = find(c, test)
        if r is not None:
            return r
    return None


def css_classes(w):
    return w.get_style_context().list_classes() if GTK3 else w.get_css_classes()


def append(box, w):
    if GTK3:
        box.pack_start(w, False, False, 0)
    else:
        box.append(w)


def add_class(w, c):
    w.get_style_context().add_class(c) if GTK3 else w.add_css_class(c)
    return w


def button(label=None, icon=None, *classes):
    if icon:
        b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON) if GTK3 else Gtk.Button.new_from_icon_name(icon)
    else:
        b = Gtk.Button(label=label)
    for c in classes:
        add_class(b, c)
    return b


# --- builders: row id -> (widget placed in the cell, function that returns the target) ---------------------------

def _header():
    hb = Gtk.HeaderBar()
    if GTK3:
        hb.set_show_close_button(True)
        hb.set_title("T")
    else:
        hb.set_show_title_buttons(True)
        hb.set_title_widget(Gtk.Label(label="T"))
    hb.set_decoration_layout("appmenu:minimize,maximize,close")
    hb.set_size_request(170, -1)
    return hb, lambda: find(hb, lambda c: isinstance(c, Gtk.Button) and c.get_visible() and "close" in css_classes(c))


def _radio():
    if GTK3:
        other = Gtk.RadioButton()
        r = Gtk.RadioButton.new_from_widget(other)
        other.set_active(True)
    else:
        other, r = Gtk.CheckButton(), Gtk.CheckButton()
        r.set_group(other)
        other.set_active(True)
    r._other = other  # keep a reference
    return r, lambda: r


def _spin_button():
    s = Gtk.SpinButton.new_with_range(0, 100, 1)
    s.set_value(5)
    return s, lambda: s


def _dropdown():
    if GTK3:
        c = Gtk.ComboBoxText()
        c.append_text("Choice")
        c.set_active(0)
    else:
        c = Gtk.DropDown.new_from_strings(["Choice"])
    return c, lambda: c


def _slider():
    s = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    s.set_value(70)
    s.set_draw_value(False)
    s.set_size_request(160, -1)
    return s, lambda: s


def _progress():
    b = Gtk.ProgressBar()
    b.set_fraction(0.5)
    b.set_size_request(160, -1)
    return b, lambda: b


def _stack(n=2):
    st = Gtk.Stack()
    for i in range(n):
        page = Gtk.Label(label=f"P{i + 1}")
        page.set_visible(True)  # GTK 3: the sidebar hides invisible pages
        st.add_titled(page, f"p{i}", f"P{i + 1}")
    return st


def _tabs():
    nb = Gtk.Notebook()
    pages = []
    for i in range(2):
        content = Gtk.Label(label=f"C{i + 1}")
        nb.append_page(content, Gtk.Label(label=f"T{i + 1}"))
        pages.append(content)
    nb.set_size_request(150, -1)

    def target():
        lab = nb.get_tab_label(pages[0])
        return lab if GTK3 else lab.get_parent()
    return nb, target


def _stack_switcher():
    st = _stack()
    sw = Gtk.StackSwitcher()
    sw.set_stack(st)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    append(box, sw)
    box._stack = st
    return box, lambda: children(sw)[0]


def _sidebar():
    st = _stack()
    sb = Gtk.StackSidebar()
    sb.set_stack(st)
    sb._stack = st
    sb.set_size_request(240, 140)
    return sb, lambda: find(sb, lambda c: isinstance(c, Gtk.ListBoxRow) and c.get_visible())


def _list():
    lb = Gtk.ListBox()
    row = Gtk.ListBoxRow()
    lab = Gtk.Label(label="List item")
    lab.set_xalign(0)
    if GTK3:
        row.add(lab)
        lb.add(row)
    else:
        row.set_child(lab)
        lb.append(row)
    lb.set_size_request(150, -1)
    return lb, lambda: row


def _adw_entry_row():
    lb = add_class(Gtk.ListBox(), "boxed-list")
    row = Adw.EntryRow(title="Field")
    lb.append(row)
    lb.set_size_request(150, -1)
    return lb, lambda: row


def _menu():
    menu = Gio.Menu()
    for t in ("Item 1", "Item 2", "Item 3"):
        menu.append(t, "app.nothing")
    b = Gtk.MenuButton()
    group = Gio.SimpleActionGroup()
    group.add_action(Gio.SimpleAction.new("nothing", None))
    b.insert_action_group("app", group)
    if GTK3:
        # Classic GtkMenu (context menus and menu buttons of GTK 3): a GTK 3 popover draws an arrow in its shape,
        # which no CSS property removes.
        b.set_use_popover(False)
    b.set_menu_model(menu)
    b.set_label("Menu")

    def open_menu():
        if GTK3:
            b.set_active(True)
            # menu at rest: no item selected (GTK 3 selects the first one on opening)
            GLib.timeout_add(200, lambda: b.get_popup().deselect() or False)
            return
        b.get_popover().popup()
        # menu at rest: without focus, no item is highlighted as it would be by the keyboard
        GLib.timeout_add(200, lambda: b.get_popover().set_focus(None) or False)
    b._open = open_menu
    return b, lambda: b


def _tooltip():
    w = Tooltip()
    add_class(w, "background")
    append(w, Gtk.Label(label="Tooltip"))
    return w, lambda: w


def _dialog():
    anchor = Gtk.Label(label="")

    def open_dialog():
        window = anchor.get_root() if not GTK3 else anchor.get_toplevel()
        if TK == "adw":
            d = Adw.AlertDialog(heading="Dialog title", body="Supporting text of the dialog.")
            d.add_response("cancel", "Cancel")
            d.add_response("ok", "Confirm")
            d.present(window)
        else:
            d = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.INFO,
                                  buttons=Gtk.ButtonsType.OK_CANCEL, text="Dialog title")
            d.format_secondary_text("Supporting text of the dialog.")
            d.show_all()
        anchor._dialog = d
    anchor._open = open_dialog
    return anchor, lambda: anchor


def _simple(w):
    return w, lambda: w


BUILDERS = {
    "header": _header,
    "button": lambda: _simple(button("Button")),
    "button-suggested": lambda: _simple(button("Confirm", None, "suggested-action")),
    "button-destructive": lambda: _simple(button("Delete", None, "destructive-action")),
    "button-flat": lambda: _simple(button("Text", None, "flat")),
    "icon-button": lambda: _simple(button(None, ICON, "circular")),
    "icon-button-flat": lambda: _simple(button(None, ICON, "circular", "flat")),
    "button-pill": lambda: _simple(button("Pill", None, "pill")),
    "toggle": lambda: _simple(Gtk.ToggleButton(label="Toggle")),
    "adw-split": lambda: _simple(Adw.SplitButton(label="Action")),
    "switch": lambda: _simple(Gtk.Switch()),
    "checkbox": lambda: _simple(Gtk.CheckButton()),
    "radio": _radio,
    "entry": lambda: _simple(Gtk.Entry(text="Text")),
    "spin-button": _spin_button,
    "dropdown": _dropdown,
    "adw-entry-row": _adw_entry_row,
    "slider": _slider,
    "progress": _progress,
    "tabs": _tabs,
    "stack-switcher": _stack_switcher,
    "sidebar": _sidebar,
    "list": _list,
    "menu": _menu,
    "tooltip": _tooltip,
    "dialog": _dialog,
}


def scaffold_css():
    """CSS of the bench itself (above the user gtk.css): the grid containers have no background and no state."""
    css = ("flowbox, flowboxchild, flowboxchild:hover, flowboxchild:selected "
           "{ background: none; box-shadow: none; outline: none; }")
    p = Gtk.CssProvider()
    if GTK3:
        p.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    else:
        p.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
