"""Expected rows: tile menu of the quick settings (surface `settings-menu`: checked test QuickMenuToggle, menu open)."""
from ._row import shell_row

# Off track: its fill (surface_container_highest) is 8 levels from the menu background in light mode, 4 in dark mode. Above
# the generic threshold (6) in light mode only, the measurement would take the fill for the track and ignore the 2 dp
# outline (48 x 28 without stroke instead of 52 x 32 with it): this threshold treats the fill as background in both modes.
SWITCH_OFF_THRESHOLD = 12

ROWS = [
    # surface_container_high, Large corners (M3E-visual in the sheet).
    shell_row("settings-menu", 5, ["normal"], {
        "normal": {"background": "@surface_container_high", "radius": "Shape.CornerLarge"}}),
    # Header icon, active tile (.header .icon.active): Filled icon button Small (40 dp, primary).
    shell_row("settings-menu-header", 5, ["normal"], {
        "normal": {"height": "SmallIconButton.ContainerHeight", "radius": "SmallIconButton.ContainerShapeRound",
                   "background": "FilledIconButton.ContainerColor", "text": "FilledIconButton.Color"}}),
    # Label of a list item (bench size).
    shell_row("settings-menu-text", 5, ["normal"], {"normal": {"text": "List.ItemLabelTextColor"}}),
    # M3E list item (List tokens): one line of 56 dp; on_surface layer; Expressive corners 4 dp at rest, 12 on hover,
    # 16 when pressed and focused (ItemHovered/Pressed/FocusedContainerExpressiveShape).
    # Hover corners (12) not measured: in light mode the 8 % layer is too pale for the corner estimate (25.6 measured
    # for 12 visible; same case as menu-item); checked in the visual review.
    shell_row("settings-menu-item", 5, ["normal", "hover", "pressed", "focus"], {
        "normal": {"background": "@surface_container_high"},
        "hover": {"height": "List.ItemOneLineContainerHeight",
                  "layer": ("List.ItemHoverLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "List.ItemPressedContainerExpressiveShape",
                    "layer": ("List.ItemPressedLabelTextColor", "State.PressedStateLayerOpacity")},
        "focus": {"radius": "List.ItemFocusedContainerExpressiveShape",
                  "layer": ("List.ItemFocusLabelTextColor", "State.FocusStateLayerOpacity")},
    }),
    # Switch (.toggle-switch of a PopupSwitchMenuItem) and checkbox (.check-box StIcon): same expectations as the
    # `switch` and `checkbox` rows of dev/m3e-bench/grid.py (GTK). Real states (off/on, empty/checked), measured at
    # rest. Differences from the GTK row: on the tile menu background (surface_container_high) the off track
    # (surface_container_highest) is below the "background colour" threshold in light mode (6 per channel), so its
    # fill is not measured here; the radius is measured on the on track, which is full (the 2 dp outline of the off
    # track skews the corner estimate: 14.5 for 16 visible).
    shell_row("settings-switch", 5, ["normal"], {
        "normal": {"height": "Switch.TrackHeight", "width": "Switch.TrackWidth",
                   "stroke": "Switch.TrackOutlineWidth"}}, threshold=SWITCH_OFF_THRESHOLD),
    shell_row("settings-switch-active", 5, ["normal"], {
        "normal": {"height": "Switch.TrackHeight", "width": "Switch.TrackWidth", "radius": "Switch.TrackShape",
                   "background": "Switch.SelectedTrackColor", "text": "Switch.SelectedHandleColor"}}),
    shell_row("settings-checkbox", 5, ["normal"], {
        "normal": {"height": "Checkbox.ContainerSize", "width": "Checkbox.ContainerSize",
                   "radius": "Checkbox.ContainerShape", "stroke": "Checkbox.UnselectedOutlineWidth",
                   "text": "Checkbox.UnselectedOutlineColor"}}),
    shell_row("settings-checkbox-active", 5, ["normal"], {
        "normal": {"height": "Checkbox.ContainerSize", "background": "Checkbox.SelectedContainerColor",
                   "text": "Checkbox.SelectedIconColor"}}),
    # Disabled checkboxes (insensitive CheckBox: :insensitive), like check:disabled of the GTK4 overrides: empty =
    # on_surface outline at 38 %; checked = on_surface fill at 38 %, surface tick. Focused checkbox: 3 dp secondary
    # ring (like the GTK ring: Checkbox.FocusIndicatorColor, 3 dp), 2 px away from the box (18 px StBin + 2 x 5).
    shell_row("settings-checkbox-disabled", 5, ["normal"], {
        "normal": {"height": "Checkbox.ContainerSize",
                   "text": ("Checkbox.UnselectedDisabledOutlineColor", "Checkbox.UnselectedDisabledContainerOpacity")}}),
    shell_row("settings-checkbox-active-disabled", 5, ["normal"], {
        "normal": {"height": "Checkbox.ContainerSize",
                   "background": ("Checkbox.SelectedDisabledContainerColor", "Checkbox.SelectedDisabledContainerOpacity"),
                   "text": "Checkbox.SelectedDisabledIconColor"}}),
    shell_row("settings-checkbox-focus", 5, ["normal"], {"normal": {"width": 28, "stroke": 3}}),
]

SURFACE = {row.id: "settings-menu" for row in ROWS}
