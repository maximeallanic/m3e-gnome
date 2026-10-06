"""Common definition of the bench: rows (widgets), states, expected values.

Shape of the expected values, per state then per measurement key (height, width, radius, stroke, background, text,
layer, dominant):
- "Comp.Key"            -> value of the token (dp, full shape, corners, or colour role);
- "@role"               -> matugen colour;
- number                -> hard-coded logical px (witnesses, values without a token: the comment says why);
- [c1, c2, c3, c4]      -> radius only: one expected value per corner (top-left, top-right, bottom-right,
                          bottom-left), each a number or a token (dp, or full shape = half the smallest measured side);
- (colour, opacity)     -> colour laid with this opacity:
    * background: on the cell background (role `surface`);
    * text      : on the expected background of the same state;
    * layer     : state layer on the background of the normal state, compared with the measured background.
"""
from dataclasses import dataclass, field

STATES = ["normal", "hover", "pressed", "focus", "disabled", "active"]
TOOLKITS = {"gtk3", "gtk4", "adw"}
CELL_BACKGROUND = "@surface"


@dataclass
class Row:
    id: str
    batch: int
    toolkits: set = field(default_factory=lambda: set(TOOLKITS))
    expected: dict = field(default_factory=dict)
    states: list = field(default_factory=lambda: list(STATES))
    # Keyword arguments of measure_cell.measure_cell for this row: `threshold` (per-channel difference under which a pixel
    # is the cell background) and `text_contrast` (smallest difference from the container for a text pixel). Rows whose
    # colours are close to their surroundings by design (Pixel tiles, 30 % disabled labels) lower them.
    measure: dict = field(default_factory=dict)

    def measure_options(self):
        """Keyword arguments of measure_cell.measure_cell for this row."""
        return dict(self.measure)


def _button(comp, size="ButtonSmall", background="ContainerColor", text="LabelTextColor",
            hover="HoverLabelTextColor", pressed="PressedLabelTextColor",
            background_off="DisabledContainerColor", opacity_off="DisabledContainerOpacity",
            text_off="DisabledLabelTextColor", text_opacity_off="DisabledLabelTextOpacity"):
    b = background if background.startswith("@") else f"{comp}.{background}"
    t = text if text.startswith("@") else f"{comp}.{text}"
    return {
        "normal": {"height": f"{size}.ContainerHeight", "radius": f"{size}.ContainerShapeRound",
                   "background": b, "text": t},
        "hover": {"height": f"{size}.ContainerHeight",
                  "layer": (t if hover is None else f"{comp}.{hover}", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": f"{size}.PressedContainerShape",
                    "layer": (t if pressed is None else f"{comp}.{pressed}", "State.PressedStateLayerOpacity")},
        "focus": {"background": b},
        "disabled": {"background": (f"{comp}.{background_off}", f"{comp}.{opacity_off}"),
                     "text": (f"{comp}.{text_off}", f"{comp}.{text_opacity_off}")},
    }


ROWS = [
    # Witness: window buttons set by hand (30 x 30), they must not move. Measuring the hover circle (8 % opacity,
    # low-contrast edge) gives 29 logical px in the three toolkits in the initial state.
    Row("header", 1, expected={"hover": {"height": 29, "width": 29}}),

    # Batch 2: buttons
    Row("button", 2, expected=_button("FilledTonalButton")),
    Row("button-suggested", 2, expected=_button("FilledButton", hover=None, pressed=None)),
    Row("button-destructive", 2, expected=_button("FilledButton", background="@error", text="@on_error",
                                                  hover=None, pressed=None)),
    # Text button: the image "default text button style states" shows it in primary, whereas
    # TextButtonTokens.LabelColor says on_surface_variant. The image is authoritative for the colour (spec § 2).
    Row("button-flat", 2, expected={
        "normal": {"text": "@primary"},
        "hover": {"height": "ButtonSmall.ContainerHeight", "radius": "ButtonSmall.ContainerShapeRound",
                  "layer": ("@primary", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "ButtonSmall.PressedContainerShape",
                    "layer": ("@primary", "State.PressedStateLayerOpacity")},
        "disabled": {"background": ("TextButton.DisabledContainerColor", "TextButton.DisabledContainerOpacity"),
                     "text": ("TextButton.DisabledLabelColor", "TextButton.DisabledLabelOpacity")},
    }),
    Row("icon-button", 2, expected={
        "normal": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                   "radius": "SmallIconButton.ContainerShapeRound", "background": "FilledTonalIconButton.ContainerColor",
                   "text": "FilledTonalIconButton.Color"},
        "hover": {"layer": ("FilledTonalIconButton.Color", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape",
                    "layer": ("FilledTonalIconButton.Color", "State.PressedStateLayerOpacity")},
    }),
    Row("icon-button-flat", 2, expected={
        "normal": {"text": "IconButton.Color"},
        "hover": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                  "radius": "SmallIconButton.ContainerShapeRound",
                  "layer": ("IconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape",
                    "layer": ("IconButton.PressedColor", "State.PressedStateLayerOpacity")},
        "disabled": {"text": ("IconButton.DisabledColor", "IconButton.DisabledOpacity")},
    }),
    Row("button-pill", 2, expected=_button("FilledTonalButton", size="ButtonMedium")),
    Row("toggle", 2, expected={
        **_button("FilledTonalButton"),
        "active": {"radius": "ButtonSmall.ContainerShapeSquare",
                   "background": "FilledTonalIconButton.SelectedContainerColor",
                   "text": "FilledTonalIconButton.SelectedColor"},
    }),
    Row("adw-split", 2, toolkits={"adw"}, expected={"normal": _button("FilledTonalButton")["normal"]}),

    # Batch 3: switch, checkbox, radio
    Row("switch", 3, expected={
        "normal": {"height": "Switch.TrackHeight", "width": "Switch.TrackWidth", "radius": "Switch.TrackShape",
                   "background": "Switch.UnselectedTrackColor", "stroke": "Switch.TrackOutlineWidth"},
        "active": {"height": "Switch.TrackHeight", "width": "Switch.TrackWidth",
                   "background": "Switch.SelectedTrackColor", "text": "Switch.SelectedHandleColor"},
        # Disabled: no measured expectation. The fill (surface_container_highest at 12 %) is invisible on the
        # background, and the outline (on_surface at 12 %) and the handle (on_surface at 38 %) have comparable
        # areas: the dominant colour flips from one to the other depending on the smoothing. Checked by visual review.
    }),
    Row("checkbox", 3, expected={
        "normal": {"height": "Checkbox.ContainerSize", "width": "Checkbox.ContainerSize",
                   "radius": "Checkbox.ContainerShape", "stroke": "Checkbox.UnselectedOutlineWidth",
                   "text": "Checkbox.UnselectedOutlineColor"},
        "active": {"height": "Checkbox.ContainerSize", "background": "Checkbox.SelectedContainerColor",
                   "text": "Checkbox.SelectedIconColor"},
    }),
    Row("radio", 3, expected={
        "normal": {"height": "RadioButton.IconSize", "width": "RadioButton.IconSize",
                   "text": "RadioButton.UnselectedIconColor"},
        "active": {"height": "RadioButton.IconSize", "text": "RadioButton.SelectedIconColor"},
    }),

    # Batch 4: fields (filled text field). 56 dp: field height without a floating label, image "text-fields".
    *[Row(i, 4, toolkits=tk, expected={
        "normal": {"height": 56, "radius": "FilledTextField.ContainerShape",
                   "background": "FilledTextField.ContainerColor", "text": "FilledTextField.InputColor"},
    }) for i, tk in (("entry", TOOLKITS), ("spin-button", TOOLKITS), ("dropdown", TOOLKITS),
                     ("adw-entry-row", {"adw"}))],

    # Batch 5: slider, progress
    # Slider at 70 %: the active part dominates. The handle is separated by the 6 dp gap, the measurement sees the
    # active track (handle, stop indicator and inner corners: visual review).
    Row("slider", 5, expected={"normal": {"height": "Slider.ActiveTrackHeight", "background": "Slider.ActiveTrackColor"}}),
    Row("progress", 5, expected={"normal": {"height": "LinearProgressIndicator.TrackThickness"}}),

    # Batch 6: menus, tooltips, dialogs: a single state (overlays do not lend themselves to forced states).
    # Corners: 16 dp for the Expressive vertical menu (image "vertical menu marked with spacing", MenuTokens only
    # knows the base menu at 4 dp). GtkAlertDialog cannot be styled: no gtk4 row for the dialog.
    # Tooltip: 24 dp high (image "measurements of a plain tooltip").
    Row("tooltip", 6, states=["normal"], expected={"normal": {
        "height": 24, "background": "PlainTooltip.ContainerColor", "text": "PlainTooltip.SupportingTextColor",
        "radius": "PlainTooltip.ContainerShape"}}),
    # Menu after the tooltip: its measurement area (under the button) must not overlap any other row.
    Row("menu", 6, states=["normal"], expected={"normal": {"background": "Menu.ContainerColor", "radius": 16}}),
    Row("dialog", 6, toolkits={"gtk3", "adw"}, states=["normal"], expected={
        "normal": {"background": "Dialog.ContainerColor", "radius": "Dialog.ContainerShape"}}),

    # Batch 7: tabs and navigation
    # Active tab: label and indicator in primary, without a container: the dominant colour is measured.
    Row("tabs", 7, expected={"active": {"dominant": "PrimaryNavigationTab.ActiveIndicatorColor"}}),
    Row("stack-switcher", 7, expected={"active": {"dominant": "PrimaryNavigationTab.ActiveIndicatorColor"}}),
    Row("sidebar", 7, expected={"active": {
        "background": "NavigationDrawer.ActiveIndicatorColor", "text": "NavigationDrawer.ActiveLabelTextColor",
        "radius": "NavigationDrawer.ActiveIndicatorShape"}}),

    # Batch 8: cross-cutting
    # List row: no background at rest, the height is measured on hover (state layer).
    Row("list", 8, expected={"normal": {"text": "List.ItemLabelTextColor"},
                             "hover": {"height": "List.ItemOneLineContainerHeight",
                                       "layer": ("List.ItemLabelTextColor", "State.HoverStateLayerOpacity")},
                             "active": {"background": "List.ItemSelectedContainerColor",
                                        "text": "List.ItemSelectedLabelTextColor",
                                        "radius": "List.ItemSelectedContainerExpressiveShape"}}),
]


def rows_for(toolkit, batch=None):
    """Rows of the toolkit; with `batch`, those of the batch plus the witnesses (batch 1)."""
    return [r for r in ROWS if toolkit in r.toolkits and (batch is None or r.batch in (1, batch))]


def references(row):
    """Every reference (tokens "Comp.Key" and roles "@x") cited by a row."""
    for state in row.expected.values():
        for v in state.values():
            for x in (v if isinstance(v, (tuple, list)) else (v,)):
                if isinstance(x, str):
                    yield x
