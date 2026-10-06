"""Expected rows: popup menus (surface `menu`: a test PopupMenu of a panel button)."""
from ._row import shell_row

ROWS = [
    # Expressive vertical menu: same references as the `menu` row of dev/m3e-bench/grid.py (Menu.ContainerColor
    # background, 16 dp corners, "vertical menu marked with spacing and padding" image) and same values as the
    # menus-bubbles-dialogs section of the GTK4 overrides (48 dp items, corners 4, on_surface layer).
    shell_row("menu", 4, ["normal"], {"normal": {"background": "Menu.ContainerColor", "radius": 16}}),
    # Middle (ornamented) item: no background at rest, height and corners measured on the state layer.
    # 48 and 4: GTK values (M3E-visual of the GTK4 menus, "spacing and padding" image). Corners measured on the 10 %
    # layer (pressed): in light mode the 8 % layer (dE ~3 against the menu background) is too pale for the
    # sub-pixel corner estimate (8.6 measured for 4 visible under magnification; 4.9 on the 10 % layer).
    shell_row("menu-item", 4, ["normal", "hover", "pressed", "focus"], {
        "normal": {"background": "Menu.ContainerColor"},
        "hover": {"height": 48, "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": 4, "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("@on_surface", "State.FocusStateLayerOpacity")},
    }),
    # Label of an item (first item, label at the bench size).
    shell_row("menu-text", 4, ["normal"], {"normal": {"text": "List.ItemLabelTextColor"}}),
    # Disabled item: on_surface label at 38 % over the menu background (label at the bench size).
    shell_row("menu-disabled", 4, ["normal"], {
        "normal": {"text": ("List.ItemDisabledLabelTextColor", "List.ItemDisabledLabelTextOpacity")}}),
    # Open submenu (unrolled in place by the Shell): surface_container_high group (same role as the unrolled menu
    # of a tile).
    shell_row("menu-submenu", 4, ["normal"], {"normal": {"background": "@surface_container_high"}}),
]

SURFACE = {
    "menu": "menu",
    "menu-item": "menu",
    "menu-text": "menu",
    "menu-disabled": "menu",
    "menu-submenu": "menu",
}
