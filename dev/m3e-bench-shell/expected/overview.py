"""Expected rows: overview (surfaces `previews`, `search`, `grid`, `folder`, `page-dots`)."""
from ._row import shell_row

STATES3 = ["normal", "hover", "pressed"]
STATES4 = ["normal", "hover", "pressed", "focus"]


def _tile_layers(ink="@on_surface"):
    """State layers of an app/search tile: `ink` layer, Large corners measured on the 10 % (pressed) layer.
    The tiles drawn on the overview background take "@overview_ink" (on_surface in dark mode, on_primary in light
    mode: the light overview is primary); those of the open folder, on their own surface, keep on_surface."""
    return {
        "hover": {"layer": (ink, "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "Shape.CornerLarge", "layer": (ink, "State.PressedStateLayerOpacity")},
        "focus": {"layer": (ink, "State.FocusStateLayerOpacity")},
    }


ROWS = [
    # Window previews first (surface `previews`, played first of the batch in the nested Shell): after the `search`
    # scenario the nested Shell sometimes stopped when the test window appeared (cause not established).
    # Window preview: close (.window-close) = Small filled icon button: 40 dp round primary, on_primary icon,
    # on_primary layer, 8 dp when pressed.
    shell_row("preview-close", 7, STATES3, {
        "normal": {"height": "SmallIconButton.ContainerHeight", "width": "SmallIconButton.ContainerHeight",
                   "radius": "SmallIconButton.ContainerShapeRound", "background": "FilledIconButton.ContainerColor",
                   "text": "FilledIconButton.Color"},
        "hover": {"layer": ("FilledIconButton.HoveredColor", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("FilledIconButton.PressedColor", "State.PressedStateLayerOpacity")},
    }),
    # Pressed corners: on a test button with the same classes (St.Button .window-close, 24 icon) set on the overview
    # background. The real button overlaps the window corner (cell background half window, half overview) and the
    # corner estimate drifts there (9.5 for 8 in dark mode).
    shell_row("preview-close-shape", 7, ["normal", "pressed"], {
        "normal": {"height": "SmallIconButton.ContainerHeight", "radius": "SmallIconButton.ContainerShapeRound"},
        "pressed": {"radius": "SmallIconButton.PressedContainerShape"},
    }),
    # Preview title (.window-caption) = Plain tooltip: same references as the `tooltip` row of dev/m3e-bench/grid.py
    # (24 dp high: "measurements of a plain tooltip" image). Text colour on a test bubble with the same classes, at the
    # bench size.
    shell_row("preview-title", 7, ["normal"], {
        "normal": {"background": "PlainTooltip.ContainerColor", "radius": "PlainTooltip.ContainerShape"}}),
    # Title height on a test bubble with the same classes, at the real size: the real preview is drawn at the scale of
    # the overview workspace (~1.04: 24 logical px measured 25.0 to 25.03 px).
    shell_row("preview-title-shape", 7, ["normal"], {
        "normal": {"height": 24, "background": "PlainTooltip.ContainerColor", "radius": "PlainTooltip.ContainerShape"}}),
    shell_row("preview-title-text", 7, ["normal"], {
        "normal": {"background": "PlainTooltip.ContainerColor", "text": "PlainTooltip.SupportingTextColor"}}),

    # Overview (background #overviewGroup = surface_dim, cell background of the surfaces below).
    # Search bar (.search-entry) = Search bar: 56 dp pill surface_container_high, typed text and leading icon on_surface
    # (InputTextColor = LeadingIconColor), label at the bench size (32 px fit in 56 dp). Hover: on_surface 8 % layer
    # (search image 11, state 2). Focus: !important ring of the stock sheet (limit), not measured.
    shell_row("search-bar", 7, ["normal", "hover"], {
        "normal": {"height": "SearchBar.ContainerHeight", "radius": "SearchBar.ContainerShape",
                   "background": "SearchBar.ContainerColor", "text": "SearchBar.InputTextColor"},
        "hover": {"height": "SearchBar.ContainerHeight",
                  "layer": ("SearchBar.InputTextColor", "State.HoverStateLayerOpacity")},
    }),
    # Hint of the empty bar (StLabel.hint-text): SupportingTextColor, on the real empty bar of the `grid` surface.
    shell_row("search-hint", 7, ["normal"], {
        "normal": {"background": "SearchBar.ContainerColor", "text": "SearchBar.SupportingTextColor"}}),
    # Container of a results section in list form (.search-section-content): Large corners, same surface as the bar
    # (surface_container_high: docked view, search image 12).
    shell_row("search-section", 7, ["normal"], {
        "normal": {"background": "@surface_container_high", "radius": "Shape.CornerLarge"}}),
    # List result (.list-search-result) = M3E list item, same references as settings-menu-item: 56 dp, on_surface
    # layer, Expressive corners 16 when pressed. Hover corners (12): the 8 % layer is too pale in light mode for the
    # corner estimate (same case as menu-item), visual review.
    shell_row("search-list", 7, STATES4, {
        "normal": {"background": "@surface_container_high"},
        "hover": {"height": "List.ItemOneLineContainerHeight",
                  "layer": ("List.ItemHoverLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "List.ItemPressedContainerExpressiveShape",
                    "layer": ("List.ItemPressedLabelTextColor", "State.PressedStateLayerOpacity")},
        # Focus: layer only. The !important ring of the stock sheet (light GNOME accent in dark mode) skews the corner
        # estimate (14.4 measured for 16 in dark mode, 16.3 in light); same 16 dp value as pressed, measured.
        "focus": {"layer": ("List.ItemFocusLabelTextColor", "State.FocusStateLayerOpacity")},
    }),
    # Default result (the one Enter launches: :selected pseudo-class set like SearchResultsView._setSelected) =
    # selected list item: secondary_container, Expressive corners 16 dp.
    shell_row("search-default", 7, ["normal"], {
        "normal": {"background": "List.ItemSelectedContainerColor",
                   "radius": "List.ItemSelectedContainerExpressiveShape"}}),
    # Title of a list result (bench size).
    shell_row("search-list-text", 7, ["normal"], {"normal": {"text": "List.ItemLabelTextColor"}}),
    # Grid result (.grid-search-result) = app-grid tile: no container, on_surface layer and Large corners. Corners
    # measured when pressed (10 % layer, same reason as search-list).
    shell_row("search-grid", 7, STATES4, _tile_layers("@overview_ink")),
    # App grid: tile (.overview-tile) like search-grid; on_surface label (bench size).
    shell_row("grid-tile", 7, STATES4, _tile_layers("@overview_ink")),
    shell_row("grid-text", 7, ["normal"], {"normal": {"text": "@overview_ink"}}),
    # Closed folder (.app-folder): container tile (folder icon preview) surface_container_high, Large corners, same
    # layer as the tiles.
    shell_row("grid-folder", 7, STATES4, {
        "normal": {"background": "@surface_container_high", "radius": "Shape.CornerLarge"},
        "hover": {"layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("@on_surface", "State.FocusStateLayerOpacity")},
    }),
    # Open folder (.app-folder-dialog) = dialog surface: same references as the `dialog` row of dev/m3e-bench/grid.py;
    # title (.folder-name-label) in Headline small on_surface (bench size).
    shell_row("folder-background", 7, ["normal"], {
        "normal": {"background": "Dialog.ContainerColor", "radius": "Dialog.ContainerShape"}}),
    # Tile with no container at rest (dialog background measured by folder-background; the dominant colour of the
    # resting tile is the icon's).
    shell_row("folder-tile", 7, STATES4, _tile_layers()),
    shell_row("folder-title", 7, ["normal"], {
        "normal": {"background": "Dialog.ContainerColor", "text": "Dialog.HeadlineColor"}}),
    # Page dots (surface `page-dots`: the Shell's PageIndicators, 3 pages, in a test .app-folder-dialog actor) =
    # Pixel PagerDots (SystemUI PagerDots.kt, onSurfaceVariant, 0.5 off the current page), lengths x 56/72: 7 px dot at
    # the current page (no 12 dp pill: St has no class for the current page, see the sheet), 7 x 2/3 = 4.7 px elsewhere
    # (6 dp x 56/72), at the 128/255 opacity of pageIndicators.js.
    shell_row("page-dots-current", 7, ["normal"], {
        "normal": {"height": 7, "width": 7, "background": "@on_surface_variant"}}),
    shell_row("page-dots-other", 7, ["normal"], {
        "normal": {"height": 4.67, "width": 4.67, "background": ("@on_surface_variant", 0.5)}}),
]

SURFACE = {
    "preview-close": "previews",
    "preview-close-shape": "previews",
    "preview-title": "previews",
    "preview-title-shape": "previews",
    "preview-title-text": "previews",
    "search-bar": "search",
    "search-hint": "grid",
    "search-section": "search",
    "search-default": "search",
    "search-list": "search",
    "search-list-text": "search",
    "search-grid": "search",
    "grid-tile": "grid",
    "grid-text": "grid",
    "grid-folder": "grid",
    "folder-background": "folder",
    "folder-tile": "folder",
    "folder-title": "folder",
    "page-dots-current": "page-dots",
    "page-dots-other": "page-dots",
}
