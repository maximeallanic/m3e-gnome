"""Expected rows: screenshot UI and on-screen keyboard (surfaces `screenshot` and `keyboard`)."""
from ._row import shell_row

STATES3 = ["normal", "hover", "pressed"]
STATES5 = ["normal", "hover", "pressed", "focus", "active"]
INNER = "ConnectedButtonGroupSmall.InnerCornerCornerSize"
OUTER = "ConnectedButtonGroupSmall.ContainerShape"

ROWS = [
    # Screenshot UI (surface `screenshot`, Main.screenshotUI.open(), no capture written). Panel
    # (.screenshot-ui-panel) = standard Floating toolbar (surface_container, full shape).
    shell_row("screenshot-panel", 9, ["normal"], {
        "normal": {"background": "FloatingToolbar.StandardContainerColor", "radius": "FloatingToolbar.ContainerShape"}}),
    # Type choice (.screenshot-ui-type-button) = Connected button group of toggle Tonal buttons. Middle button
    # ("Screen", unchecked): inner corners 8 dp (4 when pressed), secondary_container / on_secondary_container,
    # 8 / 10 / 10 % layers; checked (active) = Selected of the Tonal (secondary / on_secondary), full shape (inner
    # corners at 50 %). Height 56 dp (Medium size: icon above the label, GNOME's JS layout; the 40 dp Small size
    # holds neither, see the sheet).
    shell_row("screenshot-type", 9, STATES5, {
        "normal": {"height": "ButtonMedium.ContainerHeight", "radius": [INNER] * 4,
                   "background": "FilledTonalButton.ContainerColor", "text": "FilledTonalButton.LabelTextColor"},
        "hover": {"layer": ("FilledTonalButton.HoverLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": ["ConnectedButtonGroupSmall.PressedInnerCornerCornerSize"] * 4,
                    "layer": ("FilledTonalButton.PressedLabelTextColor", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("FilledTonalButton.FocusLabelTextColor", "State.FocusStateLayerOpacity")},
        "active": {"radius": OUTER, "background": "FilledTonalIconButton.SelectedContainerColor",
                   "text": "FilledTonalIconButton.SelectedColor"},
    }),
    # First button ("Selection"), checked on opening (visible by default).
    shell_row("screenshot-type-active", 9, ["normal"], {
        "normal": {"height": "ButtonMedium.ContainerHeight", "radius": OUTER,
                   "background": "FilledTonalIconButton.SelectedContainerColor",
                   "text": "FilledTonalIconButton.SelectedColor"}}),
    # Last button ("Window"), insensitive without a window (visible by default in the bench): disabled Tonal background
    # (on_surface 12 %). Its corners (:last-child): next row.
    shell_row("screenshot-type-disabled", 9, ["normal"], {
        "normal": {"background": ("FilledTonalButton.DisabledContainerColor",
                                   "FilledTonalButton.DisabledContainerOpacity")}}),
    # Last button of the group (active test button in a test panel, see surfaces.js: the real one touches the panel's
    # stadium curve, and its disabled background is too pale in light mode for the corner fit): full outer corners,
    # inner corners 8 dp.
    shell_row("screenshot-type-last", 9, ["normal"], {
        "normal": {"radius": [INNER, OUTER, OUTER, INNER], "background": "FilledTonalButton.ContainerColor"}}),
    # Photo / video (.screenshot-ui-shot-cast-button): second Connected button group, Small size (40 dp); photo checked
    # (the only visible button when screen recording is unavailable) = full shape, Selected of the Tonal.
    shell_row("screenshot-shot", 9, STATES3, {
        "normal": {"height": "ConnectedButtonGroupSmall.ContainerHeight", "radius": OUTER,
                   "background": "FilledTonalIconButton.SelectedContainerColor",
                   "text": "FilledTonalIconButton.SelectedColor"},
        "hover": {"layer": ("FilledTonalIconButton.SelectedHoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("FilledTonalIconButton.SelectedPressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Capture button (.screenshot-ui-capture-button): primary, round 56 dp trigger (Medium icon button size): 4 dp
    # primary ring, 4 dp of panel background, 40 dp primary disc (Small size); on_primary 8 / 10 / 10 % layers on the
    # disc. Measured on the disc (.screenshot-ui-capture-button-circle): separated from the ring by the panel
    # background, measure.py does not make one container of them; ring: visual review.
    shell_row("screenshot-button", 9, ["normal", "hover", "pressed", "focus"], {
        "normal": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                   "radius": "SmallIconButton.ContainerShapeRound", "background": "FilledIconButton.ContainerColor"},
        "hover": {"layer": ("FilledIconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("FilledIconButton.PressedColor", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("FilledIconButton.FocusedColor", "State.FocusStateLayerOpacity")},
    }),
    # "Show pointer" (.screenshot-ui-show-pointer-button, test button in a test panel: the real one touches the panel's
    # curve) = toggle Standard icon button Small; checked = secondary_container (image "4 color roles... floating
    # toolbar", element 3), Selected shape (12 dp).
    shell_row("screenshot-pointer", 9, STATES5, {
        "normal": {"text": "IconButton.Color"},
        "hover": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                  "radius": "SmallIconButton.ContainerShapeRound",
                  "layer": ("IconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("IconButton.PressedColor", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("IconButton.FocusedColor", "State.FocusStateLayerOpacity")},
        "active": {"radius": "SmallIconButton.SelectedContainerShapeRound",
                   "background": "FilledTonalIconButton.ContainerColor", "text": "FilledTonalIconButton.Color"},
    }),
    # Same button already checked (real state, checked property): Selected shape at rest, pressed shape
    # (SmallIconButton.PressedContainerShape, common to both states) measured here: on the unchecked button the
    # on_surface_variant 10 % layer over surface_container is too pale in light mode for the corner fit (9.5 for 8).
    shell_row("screenshot-pointer-checked", 9, STATES3, {
        "normal": {"height": "SmallIconButton.ContainerHeight", "radius": "SmallIconButton.SelectedContainerShapeRound",
                   "background": "FilledTonalIconButton.ContainerColor", "text": "FilledTonalIconButton.Color"},
        "hover": {"layer": ("FilledTonalIconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape",
                    "layer": ("FilledTonalIconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Tooltip (.screenshot-ui-tooltip) = Plain tooltip, same references as tooltip-dash and preview-title.
    shell_row("screenshot-tooltip", 9, ["normal"], {
        "normal": {"height": 24, "background": "PlainTooltip.ContainerColor", "radius": "PlainTooltip.ContainerShape"}}),
    shell_row("screenshot-tooltip-text", 9, ["normal"], {
        "normal": {"background": "PlainTooltip.ContainerColor", "text": "PlainTooltip.SupportingTextColor"}}),

    # On-screen keyboard (surface `keyboard`). Background (#keyboard, test keyboard) surface_dim; normal key
    # surface_bright / on_surface (M3E-visual, see the sheet: keys stand out from the background in light mode). Keys =
    # square Medium buttons (16 dp, 12 when pressed): special key (.default-key) = Tonal (secondary_container /
    # on_secondary_container). 8 / 10 % layers of the content colour.
    shell_row("keyboard-background", 9, ["normal"], {"normal": {"background": "@surface_dim"}}),
    shell_row("keyboard-key", 9, STATES3, {
        "normal": {"radius": "ButtonMedium.ContainerShapeSquare", "background": "@surface_bright",
                   "text": "@on_surface"},
        "hover": {"layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "ButtonMedium.PressedContainerShape",
                    "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
    }),
    shell_row("keyboard-special", 9, STATES3, {
        "normal": {"radius": "ButtonMedium.ContainerShapeSquare", "background": "FilledTonalButton.ContainerColor",
                   "text": "FilledTonalButton.IconColor"},
        "hover": {"layer": ("FilledTonalButton.HoverIconColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "ButtonMedium.PressedContainerShape",
                    "layer": ("FilledTonalButton.PressedIconColor", "State.PressedStateLayerOpacity")},
    }),
]

SURFACE = {row.id: "keyboard" if row.id.startswith("keyboard-") else "screenshot" for row in ROWS}
