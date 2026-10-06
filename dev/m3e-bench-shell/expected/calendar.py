"""Expected rows: calendar (surface `calendar`: the clock menu open)."""
from ._row import shell_row

STATES3 = ["normal", "hover", "pressed"]

ROWS = [
    # Container = modal Date picker (Extra large corners): the whole menu (calendar, cards, notification list).
    # surface_container background (base of the menus, like the quick settings panel) rather than
    # DatePickerModal.ContainerColor (surface_container_high): in light mode the Filled cards
    # (surface_container_highest) did not stand out against it (M3E-visual in the sheet).
    shell_row("cal-popover", 6, ["normal"], {
        "normal": {"background": "@surface_container", "radius": "DatePickerModal.ContainerShape"}}),
    # Ordinary day (.calendar-day): 40 dp round, no background at rest, on_surface (label) layer on hover and
    # pressed. Label at the real size (Body large): colour measured on another day (cal-day-text), label at 28 px
    # (two digits at 32 px do not fit in 40 dp).
    shell_row("cal-day", 6, STATES3, {
        "hover": {"height": "DatePickerModal.DateStateLayerHeight", "width": "DatePickerModal.DateStateLayerWidth",
                  "radius": "DatePickerModal.DateStateLayerShape",
                  "layer": ("DatePickerModal.DateUnselectedLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("DatePickerModal.DateUnselectedLabelTextColor", "State.PressedStateLayerOpacity")},
    }),
    shell_row("cal-day-text", 6, ["normal"], {"normal": {"text": "DatePickerModal.DateUnselectedLabelTextColor"}}),
    # Today = selected date of the Date picker (full primary; DateToday* = outline, kept for the chosen day): label
    # at 28 px. The stock sheet sets `color: -st-accent-fg-color !important` (white) on the button: on_primary is
    # set by a marked !important exception.
    shell_row("cal-today", 6, STATES3, {
        "normal": {"height": "DatePickerModal.DateContainerHeight", "width": "DatePickerModal.DateContainerWidth",
                   "radius": "DatePickerModal.DateContainerShape",
                   "background": "DatePickerModal.DateSelectedContainerColor"},
        "hover": {"layer": ("DatePickerModal.DateSelectedLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("DatePickerModal.DateSelectedLabelTextColor", "State.PressedStateLayerOpacity")},
    }),
    # Label of the current day, measured on a test day with the same classes (.calendar > .calendar-day.calendar-today,
    # 28 px label) on the witness background: inside the menu, in dark mode, on_primary is too close to the menu
    # background (surface_container), which the measure takes for the cell background and moves away from the text
    # (observed: text = background). The real day is checked under magnification in the capture.
    shell_row("cal-today-text", 6, STATES3, {
        "normal": {"background": "DatePickerModal.DateSelectedContainerColor",
                   "text": "DatePickerModal.DateSelectedLabelTextColor"},
        "hover": {"text": "DatePickerModal.DateSelectedLabelTextColor"},
        "pressed": {"text": "DatePickerModal.DateSelectedLabelTextColor"},
    }),
    # Previous / next month (.pager-button): Standard icon button Small (date-pickers image 14: 48 dp target arrows,
    # 40 container). Pressed corners (8) not measured: in light mode the 10 % layer on surface_container is too pale
    # for the corner estimate (9.5 for 8; 8.0 in dark mode; same case as menu-item).
    shell_row("cal-month-button", 6, STATES3, {
        "normal": {"text": "IconButton.Color"},
        "hover": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                  "radius": "SmallIconButton.ContainerShapeRound",
                  "layer": ("IconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("IconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Calendar cards (world clocks, events, weather) = Filled cards (cards image 06): surface_container_highest
    # background, Medium corners; on_surface (card content colour) layer on hover and pressed. Corners measured when
    # pressed: at rest, in light mode, the card (tone 90) hardly stands out from the menu (tone 94) and the corner
    # estimate drifts (12.8 to 13.4 for 12 visible). The events card, the first of the scrolling section
    # (.datemenu-displays-section.vfade), is faded at the top by the Shell: not measured (visual review).
    shell_row("cal-card-clocks", 6, STATES3, {
        "normal": {"background": "FilledCard.ContainerColor"},
        "hover": {"layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "FilledCard.ContainerShape", "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
    }),
    shell_row("cal-card-weather", 6, ["normal"], {"normal": {"background": "FilledCard.ContainerColor"}}),
]

SURFACE = {row.id: "calendar" for row in ROWS}
