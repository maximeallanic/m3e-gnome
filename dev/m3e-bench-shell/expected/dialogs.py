"""Expected rows: dialogs, run dialog, OSD, Alt+Tab, workspace switcher and dash tooltip (surfaces `dialog`,
`dialog-warning`, `run-dialog`, `osd`, `alttab`, `workspaces`, `tooltip`)."""
from ._row import shell_row

PLAIN_TOOLTIP = {"height": 24, "background": "PlainTooltip.ContainerColor", "radius": "PlainTooltip.ContainerShape"}

ROWS = [
    # Dialogs (surfaces `dialog`: ModalDialog + test MessageDialogContent; `run-dialog`: Main.openRunDialog()). Pixel
    # SystemUI dialogs (Android 17, Theme.SystemUI.Dialog; docs/design-notes.md): surface_bright background, 28 dp corners
    # (Dialog.ContainerShape token, desktop scale: see the sheet); Headline small on_surface title, Body medium
    # on_surface_variant text (labels at the bench size).
    shell_row("dialog-background", 8, ["normal"], {
        "normal": {"background": "@surface_bright", "radius": "Dialog.ContainerShape"}}),
    shell_row("dialog-title", 8, ["normal"], {
        "normal": {"background": "@surface_bright", "text": "Dialog.HeadlineColor"}}),
    shell_row("dialog-text", 8, ["normal"], {
        "normal": {"background": "@surface_bright", "text": "Dialog.SupportingTextColor"}}),
    # Default action (:default) = SystemUI Widget.Dialog.Button: full primary pill 36 dp x 56/72 = 28, no shape change
    # when pressed; label colour on the test button (next row). Focus: !important ring of the stock sheet (limit),
    # focus layer blended into the background (measured). Disabled: primary at 0.30 (qs_dialog_btn_filled_background).
    shell_row("dialog-default", 8, ["normal", "hover", "pressed", "focus", "disabled"], {
        "normal": {"height": 28, "radius": "Shape.CornerFull", "background": "FilledButton.ContainerColor"},
        "hover": {"height": 28,
                  "layer": ("FilledButton.HoveredLabelTextColor", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "Shape.CornerFull",
                    "layer": ("FilledButton.PressedLabelTextColor", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("FilledButton.FocusedLabelTextColor", "State.FocusStateLayerOpacity")},
        "disabled": {"background": ("@primary", 0.3)},
    }),
    # Test button with the same classes (:default), label at the bench size. Disabled label = on_primary at 0.30 over
    # primary at 0.30: 14 levels from its container in dark mode, under the generic text contrast (16): lowered to 8.
    shell_row("dialog-default-text", 8, ["normal", "disabled"], {
        "normal": {"background": "FilledButton.ContainerColor", "text": "FilledButton.LabelTextColor"},
        "disabled": {"background": ("@primary", 0.3), "text": ("@on_primary", 0.3)},
    }, text_contrast=8),
    # Other actions = SystemUI Widget.Dialog.Button.BorderButton: 28 pill with a 1 px primary outline, on_surface label,
    # on_surface layer; no background at rest: height and shape measured on the layer. Disabled: primary outline at
    # 0.30 (dominant colour of the cell). Height measured on the layer, set inside the outline: 28 - 2 x 1 = 26.
    shell_row("dialog-cancel", 8, ["hover", "pressed", "focus", "disabled"], {
        "hover": {"height": 26, "radius": "Shape.CornerFull",
                  "layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "Shape.CornerFull", "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("@on_surface", "State.FocusStateLayerOpacity")},
        "disabled": {"background": ("@primary", 0.3)},
    }),
    shell_row("dialog-cancel-text", 8, ["normal", "disabled"], {
        "normal": {"text": "@on_surface"},
        "disabled": {"text": ("@on_surface", 0.3)},
    }),
    # Warnings of the end-session dialog (test actors with the real classes: .end-session-dialog >
    # .end-session-dialog-battery-warning and .dialog-list > .dialog-list-title, text at the bench size): M3 error roles
    # (error_container / on_error_container) instead of the stock amber (#cd9309 on 10 % amber).
    shell_row("dialog-warning", 8, ["normal"], {
        "normal": {"background": "@error_container", "text": "@on_error_container"}}),
    shell_row("dialog-list-warning", 8, ["normal"], {
        "normal": {"background": "@error_container", "text": "@on_error_container"}}),
    # Run dialog: same dialog surface; description (.run-dialog-description) in Body medium on_surface_variant.
    shell_row("run-background", 8, ["normal"], {
        "normal": {"background": "@surface_bright", "radius": "Dialog.ContainerShape"}}),
    shell_row("run-description", 8, ["normal"], {
        "normal": {"background": "@surface_bright", "text": "Dialog.SupportingTextColor"}}),
    # Entry (.run-dialog-entry, StEntry of the dialogs) = Filled text field, same expectations as the `entry` row of
    # grid.py (56 dp with no floating label, top corners 4 dp). Test entry on the witness background (see surfaces.js:
    # in light mode the real entry is below the "background colour" threshold of measure.py). Hover: on_surface 8 %
    # layer; focus (state visible when opened): !important ring of the stock sheet (limit), entry background measured.
    shell_row("run-entry", 8, ["normal", "hover", "focus"], {
        "normal": {"height": 56, "radius": "FilledTextField.ContainerShape",
                   "background": "FilledTextField.ContainerColor", "text": "FilledTextField.InputColor"},
        "hover": {"layer": ("FilledTextField.InputColor", "State.HoverStateLayerOpacity")},
        "focus": {"background": "FilledTextField.ContainerColor"},
    }),
    # OSD (surface `osd`) = Pixel volume panel (VolumeDialog: surface background, pill; docs/design-notes.md), level at the slider
    # track (40 dp x 56/72 = 31, active part primary, dominant at 60 %), on_surface icon and label.
    shell_row("osd-background", 8, ["normal"], {
        "normal": {"background": "@surface", "radius": "Shape.CornerFull"}}),
    shell_row("osd-level", 8, ["normal"], {"normal": {"height": 31, "background": "Slider.ActiveTrackColor"}}),
    shell_row("osd-icon", 8, ["normal"], {"normal": {"text": "@on_surface"}}),
    shell_row("osd-text", 8, ["normal"], {"normal": {"background": "@surface", "text": "@on_surface"}}),
    # Alt+Tab (surface `alttab`): surface_container_high list, Extra large corners; selected item = secondary_container
    # (List.ItemSelected*), Large corners (28 - 12 of inner margin); other item: on_surface layer; labels at the bench
    # size.
    shell_row("alttab-list", 8, ["normal"], {
        "normal": {"background": "@surface_container_high", "radius": "Shape.CornerExtraLarge"}}),
    shell_row("alttab-selected", 8, ["normal"], {
        "normal": {"background": "List.ItemSelectedContainerColor", "radius": "Shape.CornerLarge"}}),
    shell_row("alttab-selected-text", 8, ["normal"], {"normal": {"text": "List.ItemSelectedLabelTextColor"}}),
    shell_row("alttab-item", 8, ["hover", "pressed", "focus"], {
        "hover": {"layer": ("@on_surface", "State.HoverStateLayerOpacity")},
        "pressed": {"radius": "Shape.CornerLarge", "layer": ("@on_surface", "State.PressedStateLayerOpacity")},
        "focus": {"layer": ("@on_surface", "State.FocusStateLayerOpacity")},
    }),
    shell_row("alttab-item-text", 8, ["normal"], {"normal": {"text": "@on_surface"}}),
    # Workspace switcher (surface `workspaces`): surface_container_high container, Extra large corners (pill: 56 dp
    # high); active workspace = 32 x 16 dp secondary_container pill (on_secondary_container content, inner pill: see the
    # sheet); inactive workspace = 8 dp on_surface_variant dot.
    shell_row("workspaces-background", 8, ["normal"], {
        "normal": {"background": "@surface_container_high", "radius": "Shape.CornerExtraLarge"}}),
    shell_row("workspaces-active", 8, ["normal"], {
        "normal": {"height": 16, "width": 32, "background": "@secondary_container", "text": "@on_secondary_container"}}),
    shell_row("workspaces-inactive", 8, ["normal"], {
        "normal": {"height": 8, "width": 8, "background": "@on_surface_variant"}}),
    # Dash tooltip (.dash-label, surface `tooltip`) = Plain tooltip, same references as the `tooltip` row of grid.py and
    # as preview-title; text colour on a test bubble at the bench size.
    shell_row("tooltip-dash", 8, ["normal"], {"normal": dict(PLAIN_TOOLTIP)}),
    shell_row("tooltip-dash-text", 8, ["normal"], {
        "normal": {"background": "PlainTooltip.ContainerColor", "text": "PlainTooltip.SupportingTextColor"}}),
]

SURFACE = {
    "dialog-background": "dialog",
    "dialog-title": "dialog",
    "dialog-text": "dialog",
    "dialog-default": "dialog",
    "dialog-default-text": "dialog",
    "dialog-cancel": "dialog",
    "dialog-cancel-text": "dialog",
    "dialog-warning": "dialog-warning",
    "dialog-list-warning": "dialog-warning",
    "run-background": "run-dialog",
    "run-description": "run-dialog",
    "run-entry": "run-dialog",
    "osd-background": "osd",
    "osd-level": "osd",
    "osd-icon": "osd",
    "osd-text": "osd",
    "alttab-list": "alttab",
    "alttab-selected": "alttab",
    "alttab-selected-text": "alttab",
    "alttab-item": "alttab",
    "alttab-item-text": "alttab",
    "workspaces-background": "workspaces",
    "workspaces-active": "workspaces",
    "workspaces-inactive": "workspaces",
    "tooltip-dash": "tooltip",
    "tooltip-dash-text": "tooltip",
}
