# overrides

Stylesheets and templates that restyle GTK 3, GTK 4 / libadwaita, Chrome and the Ptyxis terminal in Material 3 Expressive.
The installer copies them flat into `~/.config/m3e-gnome/overrides/` and loads them from `~/.config/gtk-3.0/gtk.css` and
`~/.config/gtk-4.0/gtk.css` (`lib/steps_config.sh`, `write_gtk_imports`). Always install the whole directory: the index
files `@import` their parts by relative url.

| File | Role |
| --- | --- |
| `m3e-gtk4.css` + `m3e-gtk4-*.css` | M3E components for GTK 4 (index + parts; cascade order = import order). Colours are `var(--role)`. Rules use `:not(#m3e)` to get id-level specificity (GTK does not count `:not()`), which `window-buttons-gtk4.css` shares. |
| `m3e-gtk3.css` + `m3e-gtk3-*.css` | Same for GTK 3 (colours are `@role`, no CSS variables). |
| `m3e-point-radio-symbolic.svg` | Dot used by the radio button. |
| `window-buttons-gtk3.css`, `window-buttons-gtk4.css` | One title-bar geometry everywhere (40 px bar, 30 px round buttons), including Chrome and mutter X11 frames. |
| `no-bold-gtk3.css`, `no-bold-gtk4.css` | The theme has a strict no-bold rule; GTK 4 also pins the variable-font `wght` axis. |
| `chrome-dark-gtk4.template` | matugen template: Chrome toolbar and active tab in dark colours even in a light theme (renders `chrome-dark-gtk4.css`, imported by `window-buttons-gtk4.css`). |
| `ptyxis-material.palette` | matugen template of the Ptyxis terminal palette (`[Light]` and `[Dark]` rendered together). |
| `event-dot.svg.template`, `event-dot-dimmed.svg.template`, `event-dot-today.svg.template` | matugen templates of the Shell calendar's "day with events" dots (on_surface, on_surface at 38 % outside the month, on_primary on today), rendered into `~/.themes/M3E-Shell/gnome-shell/assets/`. |
| `gnome-accent.template`, `papirus-folders.template` | Empty templates whose only job is to trigger a matugen `post_hook` with the closest preset colour. |

## Optional: Ptyxis active tab in the terminal's colour

With the default "Material" palette nothing is needed. If you pick another Ptyxis palette, `theme/bin/ptyxis-active-tab`
generates `~/.config/m3e-gnome/ptyxis-active-tab.css` (the active tab takes the terminal's background and foreground).
This is a manual step, as in the original setup: the installer and `material-sync` neither run it nor import its output.
Run `python3 theme/bin/ptyxis-active-tab` after choosing the palette and append
`@import url("file:///home/USER/.config/m3e-gnome/ptyxis-active-tab.css");` to `~/.config/gtk-4.0/gtk.css`
(uninstalling restores the original file). Limits: only the default profile is read; a translucent terminal keeps an opaque tab.

Conventions: every numeric value cites a design token (`dev/reference/m3e-tokens.json`) or carries an
`M3E-visual: <reason>` comment; checked by `dev/m3e-bench/verify_tokens.py`. Inputs: the matugen-rendered
`colors.css`. Outputs: none (static styling).
