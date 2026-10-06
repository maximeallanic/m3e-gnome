"""Expected rows: notifications (surfaces `notifications`, `notifications-buttons`, `notifications-group`, `banner`:
test notifications of the nested Shell inside the calendar list)."""
from ._row import shell_row

STATES3 = ["normal", "hover", "pressed"]
# Pixel welded cards (Android 17, SystemUI; docs/design-notes.md): surfaceEffect1 at its opacity over the calendar background
# (surface_container), rendered opaque.
CARD_BACKGROUND = ("@surface_effect_1", "@surface_effect_1", "@surface_container")

# The card is darker than the calendar by 4 to 5 levels per channel in dark mode (surfaceEffect1 over surface_container),
# below the generic background threshold of the measurement (6): the card rows pass this one, the captures being
# lossless renders. Without it the card is invisible and the measurement takes the icon badge for its background.
CARD_THRESHOLD = 2

ROWS = [
    # Cards: radius 28 dp x 56/72 = 22 at the ends of the list, 4 dp x 56/72 = 3 at the joints. Position pseudo-classes
    # (:m3e-first / :m3e-last, set by m3e-motion in a session) are set by the bench: reminder first, group stack in
    # the middle, media message last. The 2 px gap (extensions sheet) is not loaded here.
    # Top card of the group stack (three notifications, middle of the list): background only (the stacked cards
    # stick out at the bottom).
    shell_row("notif-card", 6, ["normal"], {"normal": {"background": CARD_BACKGROUND}}, threshold=CARD_THRESHOLD),
    # Single notification of its source, expanded (actions visible), first of the list: shape and layers of the card.
    # Corners measured when pressed (same reason as cal-card-clocks). Corners per corner: top-left, top-right,
    # bottom-right, bottom-left.
    shell_row("notif-card-actions", 6, STATES3, {
        "normal": {"background": CARD_BACKGROUND},
        "hover": {"layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": [22, 22, 3, 3], "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
    }, threshold=CARD_THRESHOLD),
    # Media message (MediaMessage classes, test actor without MPRIS player), last of the list: same card.
    shell_row("notif-media", 6, ["normal", "pressed"], {
        "normal": {"background": CARD_BACKGROUND},
        "pressed": {"radius": [3, 3, 22, 22]}}, threshold=CARD_THRESHOLD),
    # "Clear all" (.message-list-clear-button) = Tonal button Small.
    shell_row("notif-clear", 6, STATES3, {
        "normal": {"height": "ButtonSmall.ContainerHeight", "radius": "ButtonSmall.ContainerShapeRound",
                   "background": "FilledTonalButton.ContainerColor"},
        "hover": {"layer": ("FilledTonalButton.HoverLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "ButtonSmall.PressedContainerShape",
                    "layer": ("FilledTonalButton.PressedLabelTextColor", "State.PressedStateLayerOpacity")},
    }),
    # Notification action (.notification-button) = Pixel text button (NotificationAction: no background, primary
    # label, 48 dp x 56/72 = 37 high); no container at rest: height and shape measured on the primary layer.
    shell_row("notif-action", 6, STATES3, {
        "hover": {"height": 37, "radius": "Shape.CornerFull",
                  "layer": ("@primary", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "Shape.CornerFull", "layer": ("@primary", "State.PressedStateLayerOpacity")},
    }),
    # Close (.message-close-button, card header) = Standard icon button XSmall (32 dp).
    shell_row("notif-close", 6, STATES3, {
        "hover": {"height": "XSmallIconButton.ContainerHeight", "width": "XSmallIconButton.ContainerHeight",
                  "radius": "XSmallIconButton.ContainerShapeRound",
                  "layer": ("IconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "XSmallIconButton.PressedContainerShape",
                    "layer": ("IconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Expand button of the reminder (.message-expand-button, pill carried by its icon) = Pixel expand button
    # (notification_2025_expand_button_pill 26 x 18 dp x 56/72 = 20 x 14, surfaceEffect3 at its opacity over the card).
    shell_row("notif-expand", 6, ["normal"], {
        "normal": {"height": 14, "width": 20, "radius": "Shape.CornerFull",
                   "background": ("@surface_effect_3", "@surface_effect_3")}}),
    # Media button (.message-media-control) = Standard icon button Small.
    shell_row("notif-media-button", 6, STATES3, {
        "normal": {"text": "IconButton.Color"},
        "hover": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                  "radius": "SmallIconButton.ContainerShapeRound",
                  "layer": ("IconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape",
                    "layer": ("IconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Collapse the group (.message-collapse-button, expanded group) = Tonal icon button XSmall.
    shell_row("notif-collapse", 6, STATES3, {
        "normal": {"height": "XSmallIconButton.ContainerHeight", "width": "XSmallIconButton.ContainerHeight",
                   "radius": "XSmallIconButton.ContainerShapeRound", "background": "FilledTonalIconButton.ContainerColor",
                   "text": "FilledTonalIconButton.Color"},
        "hover": {"layer": ("FilledTonalIconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "XSmallIconButton.PressedContainerShape",
                    "layer": ("FilledTonalIconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Banner (surface `banner`: CRITICAL notification shown by messageTray): same card, isolated (radius 22 everywhere),
    # same opaque background as the list cards (surfaceEffect1 over surface_container), floating (level 3 shadow,
    # visual review). Hover: St only draws a shadow, the banner keeps its level 3 shadow with no state layer (limit):
    # background unchanged.
    shell_row("notif-banner", 6, ["normal", "hover"], {
        "normal": {"background": CARD_BACKGROUND, "radius": 22},
        "hover": {"background": CARD_BACKGROUND},
    }),
]

SURFACE = {
    "notif-card": "notifications",
    "notif-card-actions": "notifications",
    "notif-media": "notifications",
    "notif-clear": "notifications",
    "notif-action": "notifications-buttons",
    "notif-close": "notifications-buttons",
    "notif-media-button": "notifications-buttons",
    "notif-expand": "notifications-buttons",
    "notif-collapse": "notifications-group",
    "notif-banner": "banner",
}
