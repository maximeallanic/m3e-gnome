"""Expected rows: lock screen, unlock prompt and login screen.

Surfaces `lock`, `lock-media`, `lock-media-button`, `unlock` (nested Shell locked) and `login`, `login-prompt` (nested
Shell in gdm mode). The screen is always dark (like GDM, whose frozen sheet is dark, and like the stock sheet which keeps
light text on the dimmed wallpaper): roles of the dark palette in both modes ("@dark.role", measure.colors_for).
Clock Display large, entry = Filled text field (`entry` row of grid.py), Tonal buttons, user list = list items.
"""
from ._row import shell_row

STATES3 = ["normal", "hover", "pressed"]
STATES4 = ["normal", "hover", "pressed", "focus"]


def _tonal_icon_button(size):
    """Filled tonal icon button on the dark palette: secondary_container, on_secondary_container layers."""
    layer = "@dark.on_secondary_container"
    return {
        "normal": {"height": f"{size}IconButton.ContainerHeight", "radius": f"{size}IconButton.ContainerShapeRound",
                   "background": "@dark.secondary_container", "text": layer},
        "hover": {"layer": (layer, "State.HoverStateLayerOpacity")},
        "pressed": {"radius": f"{size}IconButton.PressedContainerShape",
                    "layer": (layer, "State.PressedStateLayerOpacity")},
        "focus": {"layer": (layer, "State.FocusStateLayerOpacity")},
    }


def _bar_button():
    """Bar button on the dark palette: same expectations as bar-button (batch 4), without the active state."""
    ink = "@dark.on_surface"
    return {
        "normal": {"text": ink},
        "hover": {"height": "XSmallIconButton.ContainerHeight", "radius": "XSmallIconButton.ContainerShapeRound",
                  "layer": (ink, "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "XSmallIconButton.SelectedContainerShapeRound", "background": "@dark.primary"},
        "focus": {"layer": (ink, "State.FocusStateLayerOpacity")},
    }


def _password_entry():
    """Password entry (.login-dialog-prompt-entry) = Filled text field on the dark palette."""
    return {
        "normal": {"height": 56, "radius": "FilledTextField.ContainerShape",
                   "background": "@dark.surface_container_highest", "text": "@dark.on_surface"},
        "hover": {"layer": ("@dark.on_surface", "State.HoverStateLayerOpacity")},
        "focus": {"background": "@dark.surface_container_highest"},
    }


ROWS = [
    # Clock: colour on the 57 px glyphs of the real clock; size on a gauge with the same classes (height 1 em = font
    # size set by the sheet).
    shell_row("lock-clock", 10, ["normal"], {"normal": {"text": "@dark.on_surface"}}),
    shell_row("lock-clock-size", 10, ["normal"], {"normal": {"height": "TypeScale.DisplayLargeSize"}}),
    # Date (bench size): secondary text on_surface_variant.
    shell_row("lock-date", 10, ["normal"], {"normal": {"text": "@dark.on_surface_variant"}}),
    # Lock screen bar (#panel.unlock-screen): same buttons as bar-button (batch 4), dark palette (dimmed wallpaper
    # below).
    shell_row("lock-bar-button", 10, STATES4, _bar_button()),
    # Password entry (.login-dialog-prompt-entry) = Filled text field, same expectations as `entry` of grid.py and
    # run-entry (batch 8), dark palette; test text (password dots) at the bench size.
    shell_row("lock-entry", 10, ["normal", "hover", "focus"], _password_entry()),
    # User name (Headline small, bench size) and default avatar (Filled tonal: secondary_container, on_secondary_container
    # icon, full shape).
    shell_row("lock-user", 10, ["normal"], {"normal": {"text": "@dark.on_surface"}}),
    shell_row("lock-avatar", 10, ["normal"], {
        "normal": {"radius": "Shape.CornerFull", "background": "@dark.secondary_container",
                   "text": "@dark.on_secondary_container"}}),
    # "Switch user" = Filled tonal icon button Medium (56 dp), on_secondary_container layers.
    shell_row("lock-switch-user", 10, STATES4, _tonal_icon_button("Medium")),
    # Media message of the lock screen (.unlock-dialog-notifications-container .message, MediaMessage): Filled card on
    # the dark palette, like notif-media (batch 6); title on_surface, body on_surface_variant (bench size), icon =
    # secondary_container badge, button = Standard icon button Small (IconButton.Color = on_surface_variant).
    shell_row("lock-media", 10, ["normal"], {"normal": {"background": "@dark.surface_container_highest"}}),
    shell_row("lock-media-title", 10, ["normal"], {"normal": {"text": "@dark.on_surface"}}),
    shell_row("lock-media-body", 10, ["normal"], {"normal": {"text": "@dark.on_surface_variant"}}),
    shell_row("lock-media-icon", 10, ["normal"], {"normal": {"background": "@dark.secondary_container"}}),
    shell_row("lock-media-button", 10, ["normal"], {"normal": {"text": "@dark.on_surface_variant"}}),
    shell_row("lock-media-button-states", 10, ["hover", "pressed"], {
        "hover": {"height": "SmallIconButton.ContainerHeight", "radius": "SmallIconButton.ContainerShapeRound",
                  "layer": ("@dark.on_surface_variant", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape",
                    "layer": ("@dark.on_surface_variant", "State.PressedStateLayerOpacity")},
    }),
    # User list: item = M3E list item set alone (cards spaced by 12): surface_container, Large corners (16); on_surface
    # 8 / 10 / 10 % layers (List.Item*LabelTextColor = on_surface). Name at the bench size.
    shell_row("login-user", 10, STATES4, {
        "normal": {"radius": "Shape.CornerLarge", "background": "@dark.surface_container"},
        "hover": {"layer": ("@dark.on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "List.ItemPressedContainerExpressiveShape",
                    "layer": ("@dark.on_surface", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("@dark.on_surface", "State.FocusStateLayerOpacity")},
    }),
    shell_row("login-user-text", 10, ["normal"], {"normal": {"text": "@dark.on_surface"}}),
    # "Not listed?" = Text button Small (primary label, like `button-flat` of grid.py), no container at rest; label
    # colour on a test button with the same classes (bench size).
    shell_row("login-not-listed", 10, ["hover", "pressed", "focus"], {
        "hover": {"height": "ButtonSmall.ContainerHeight", "radius": "ButtonSmall.ContainerShapeRound",
                  "layer": ("@dark.primary", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "ButtonSmall.PressedContainerShape",
                    "layer": ("@dark.primary", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("@dark.primary", "State.FocusStateLayerOpacity")},
    }),
    shell_row("login-not-listed-text", 10, ["normal"], {"normal": {"text": "@dark.primary"}}),
    # Bottom buttons (accessibility, session choice) and "switch user": Filled tonal icon button Medium.
    shell_row("login-a11y", 10, STATES4, _tonal_icon_button("Medium")),
    # Login screen bar (#panel.login-screen): like lock-bar-button.
    shell_row("login-bar-button", 10, STATES4, _bar_button()),
    # Login prompt: entry (like lock-entry), cancel = Filled tonal icon button Small (40 dp, next to the entry),
    # session choice = Filled tonal icon button Medium.
    shell_row("login-entry", 10, ["normal", "hover", "focus"], _password_entry()),
    shell_row("login-cancel", 10, STATES4, _tonal_icon_button("Small")),
    shell_row("login-session", 10, STATES4, _tonal_icon_button("Medium")),
]

SURFACE = {
    "lock-clock": "lock",
    "lock-clock-size": "lock",
    "lock-date": "lock",
    "lock-bar-button": "lock",
    "lock-entry": "unlock",
    "lock-user": "unlock",
    "lock-avatar": "unlock",
    "lock-switch-user": "unlock",
    "lock-media": "lock-media",
    "lock-media-title": "lock-media",
    "lock-media-body": "lock-media",
    "lock-media-icon": "lock-media",
    "lock-media-button": "lock-media",
    "lock-media-button-states": "lock-media-button",
    "login-user": "login",
    "login-user-text": "login",
    "login-not-listed": "login",
    "login-not-listed-text": "login",
    "login-a11y": "login",
    "login-bar-button": "login",
    "login-entry": "login-prompt",
    "login-cancel": "login-prompt",
    "login-session": "login-prompt",
}

# Surfaces captured by a nested Shell in login-screen mode (run.sh: nested.sh --mode gdm); the others in user mode.
SURFACES_GDM = {"login", "login-prompt"}
