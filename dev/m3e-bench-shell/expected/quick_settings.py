"""Expected rows: quick settings panel (surface `settings`: open panel, test tiles with the Shell's classes)."""
from ._row import shell_row

# Resting tile background: Pixel surfaceEffect1 (neutral 98 / 6 at 0.54, CustomDynamicColors) over the panel.
TILE_BACKGROUND = ("@surface_effect_1", 0.54)
# That tile is darker than the panel by 5 levels per channel (dark mode), below the generic background threshold of the
# measurement (6): the tile rows pass this one, the captures being lossless renders.
TILE_THRESHOLD = 2

ROWS = [
    # Panel: surface_container, Extra large corners.
    shell_row("settings-panel", 5, ["normal"], {
        "normal": {"background": "@surface_container", "radius": "Shape.CornerExtraLarge"}}),
    # Tiles = Pixel tiles (Android 17, SystemUI Tile.kt / CommonTile.kt, shade_dimens.xml; docs/design-notes.md),
    # lengths x 56/72
    # (desktop density, user choice of 2026-10-05). Inactive background surfaceEffect1 mixed with the panel
    # background. Desktop state layers (State tokens). Focus: !important ring of the stock sheet (GNOME accent, blue in
    # the bench, primary in a session through the gnome-accent hook; no drawable focus layer): the ring is drawn inside
    # the tile (2 px inset shadow: 52 x 26 visible fill), its colour is not the theme's.
    # Simple tile (.quick-toggle) = single-target tile: inactive pill, 24 dp radius (19 px) and primary when active.
    shell_row("settings-tile", 5, ["normal", "hover", "pressed", "focus", "active", "disabled"], {
        "normal": {"height": 56, "radius": 28, "background": TILE_BACKGROUND, "text": "@on_surface"},
        "hover": {"height": 56, "radius": 28, "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": 28, "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "focus": {"height": 52, "radius": 26},
        "active": {"height": 56, "radius": 19, "background": "@primary", "text": "@on_primary"},
        "disabled": {"background": ("@surface", 0.18), "text": ("@on_surface_variant", 0.38)},
    }, threshold=TILE_THRESHOLD),
    # Tile with a menu (.quick-toggle-has-menu) = dual-target tile: surfaceEffect1 background carried by the container
    # in both states, main half transparent (state layers only, corners of the left half of the pill). The icon badge
    # (44 px, primary when active): visual review. Corners per corner: top-left, top-right, bottom-right, bottom-left.
    shell_row("settings-split", 5, ["normal", "hover", "pressed", "active"], {
        "normal": {"height": 56, "radius": [28, 0, 0, 28], "background": TILE_BACKGROUND, "text": "@on_surface"},
        "hover": {"radius": [28, 0, 0, 28], "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": [28, 0, 0, 28], "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "active": {"background": TILE_BACKGROUND},
    }, threshold=TILE_THRESHOLD),
    # Menu button (.quick-toggle-menu-button): 20 px chevron in 40 px, no background, onSurfaceVariant (the Pixel has
    # no menu button). Its container is the right end of the tile pill, cut by the 40 px cell: height and corners of
    # the pill are measured on the main half (settings-split), not here (the middle column of the cell crosses the
    # curved end: 53.9 for 56). St clamps the corners of its own layer to half its width: 20 px, not 28.
    shell_row("settings-split-menu", 5, ["normal", "hover", "pressed", "active"], {
        "normal": {"width": 40, "background": TILE_BACKGROUND, "text": "@on_surface_variant"},
        "hover": {"radius": [0, 20, 20, 0], "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": [0, 20, 20, 0], "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "active": {"background": TILE_BACKGROUND, "text": "@on_surface_variant"},
    }, threshold=TILE_THRESHOLD),
    # Slider (.slider of a QuickSlider, at 70 %) = Pixel BrightnessSlider (Android 17: 40 dp track x 56/72 = 31,
    # active primary; docs/design-notes.md): the active part dominates. Corners 9 / 2, gap and bar handle are drawn by the
    # m3e-motion extension (slider component), absent from the bench (visual review in a session).
    shell_row("settings-slider", 5, ["normal"], {
        "normal": {"height": 31, "background": "Slider.ActiveTrackColor"}}),
    # Short slider (40 px .slider at 0 %, on the witness background): St's round handle is only 4 px (-slider-handle-
    # radius 2: the 4 x 40 bar handle is drawn by m3e-motion, absent from the bench); the cell therefore measures the
    # inactive track: 31 px, surfaceEffect1 at its opacity.
    shell_row("settings-slider-handle", 5, ["normal"], {
        "normal": {"height": 31, "background": ("@surface_effect_1", "@surface_effect_1")}}),
    # Tile titles (native and test) no more truncated than in the stock sheet, in the bench locale
    # ($M3E_BENCH_LOCALE): black witness 12 px wide, plus 12 px per title cut by an ellipsis (Pango, ClutterText)
    # whose visible share is below the stock one (a title absent from the stock table: any ellipsis is a failure);
    # titles and widths are in the nested Shell's log. Widths are compared, never character counts.
    shell_row("settings-titles", 5, ["normal"], {"normal": {"width": 12}}),
    # Battery (.quick-toggle.power-item of the system row): Tonal button Small (icon + percentage).
    shell_row("settings-battery", 5, ["normal"], {
        "normal": {"height": "ButtonSmall.ContainerHeight", "radius": "ButtonSmall.ContainerShapeRound",
                   "background": "FilledTonalButton.ContainerColor", "text": "FilledTonalButton.LabelTextColor"}}),
    # System buttons (.quick-settings-system-item .icon-button): Tonal icon button Small (40 dp, 24 dp icon).
    shell_row("settings-system", 5, ["normal", "hover", "pressed"], {
        "normal": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                   "radius": "SmallIconButton.ContainerShapeRound", "background": "FilledTonalIconButton.ContainerColor",
                   "text": "FilledTonalIconButton.Color"},
        "hover": {"layer": ("FilledTonalIconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape",
                    "layer": ("FilledTonalIconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
]

SURFACE = {row.id: "settings" for row in ROWS}
