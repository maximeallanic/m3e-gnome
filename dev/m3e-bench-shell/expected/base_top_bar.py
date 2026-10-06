"""Expected rows: witness, base of the sheet and top bar (surfaces `bar` and `base`)."""
from ._row import STATES, shell_row

ROWS = [
    # Witness: the top bar keeps its layout (full width, translucent, 36 px): its height must not move between
    # batches. Hard-coded value, no token (a GNOME bar, not an M3E component).
    shell_row("witness-bar", 2, STATES, {"normal": {"height": 36}}),

    # Base of the sheet (font, base colours), test actors posed by the `base` surface.
    # Plain text outside any component: colour inherited from `stage`.
    shell_row("type-body", 3, ["normal"], {"normal": {"text": "@on_surface"}}),
    # Base surface of dialogs (empty test .modal-dialog): surface_bright (Pixel Theme.SystemUI.Dialog).
    shell_row("modal-background", 3, ["normal"], {"normal": {"background": "@surface_bright"}}),

    # Top bar (surface `bar`, states forced on the panel buttons). Layout kept: full width, translucent, 36 px
    # (witness). Content colour: on_surface (M3E-visual in 10-top-bar.css: design choice, one tone whiter than the
    # token's on_surface_variant); state layer = content colour at 8 / 10 % (State tokens). There is no separate
    # pressed layer: a press takes the selected look (the Shell sets :active on a brief press).
    # Resting colour of the icons is measured on the quick settings button; the clock (16 px text, anti-aliased
    # blends) is only measured when active, on its container (resting colour: visual review).
    # Icon button of the bar (quick settings) = Standard icon button XSmall (32 dp in a 36 px bar); open menu
    # (:checked) = selected Filled toggle icon button (primary background, square shape 12 dp).
    shell_row("bar-button", 4, ["normal", "hover", "pressed", "focus", "active"], {
        "normal": {"text": "@on_surface"},
        "hover": {"height": "XSmallIconButton.ContainerHeight", "radius": "XSmallIconButton.ContainerShapeRound",
                  "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "XSmallIconButton.SelectedContainerShapeRound",
                    "background": "FilledIconButton.SelectedContainerColor"},
        "focus": {"layer": ("@on_surface", "State.FocusStateLayerOpacity")},
        "active": {"height": "XSmallIconButton.ContainerHeight",
                   "radius": "XSmallIconButton.SelectedContainerShapeRound",
                   "background": "FilledIconButton.SelectedContainerColor", "text": "FilledIconButton.SelectedColor"},
    }),
    # Clock = Text button XSmall (pill on hover, on .clock); open calendar (and press) = Filled button (primary
    # background, on_primary label, round shape).
    shell_row("bar-clock", 4, ["normal", "hover", "pressed", "focus", "active"], {
        "hover": {"height": "ButtonXSmall.ContainerHeight", "radius": "ButtonXSmall.ContainerShapeRound",
                  "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "ButtonXSmall.ContainerShapeRound", "background": "FilledButton.ContainerColor"},
        "focus": {"layer": ("@on_surface", "State.FocusStateLayerOpacity")},
        "active": {"height": "ButtonXSmall.ContainerHeight", "radius": "ButtonXSmall.ContainerShapeRound",
                   "background": "FilledButton.ContainerColor", "text": "FilledButton.LabelTextColor"},
    }),
    # Messages indicator of the date button (St.Icon .messages-indicator, made visible by the bench): child of the
    # .clock-display button outside the .clock pill, on_surface in every state (with the calendar open the primary
    # pill only surrounds .clock).
    shell_row("bar-clock-indicator", 4, ["normal", "active"], {
        "normal": {"text": "@on_surface"}, "active": {"text": "@on_surface"}}),
    # Workspace indicator: the dots are on_surface; the dot of the active workspace stretches into a full pill.
    shell_row("bar-indicator", 4, ["normal"], {
        "normal": {"background": "@on_surface", "radius": "Shape.CornerFull"}}),
]

SURFACE = {
    "witness-bar": "bar",
    "type-body": "base",
    "modal-background": "base",
    "bar-button": "bar",
    "bar-clock": "bar",
    "bar-indicator": "bar",
    "bar-clock-indicator": "bar",
}
