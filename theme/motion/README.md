# motion

`gtk/` holds the M3E spring table for GTK, **generated** by the m3e-motion generator (do not edit by hand).

- `gtk/m3e-gtk4-motion.css`: `--m3e-spring-<name>-curve` and `--m3e-spring-<name>-duration` variables on `:root`
  (names: default/fast/slow x spatial/effects). Imported by `~/.config/gtk-4.0/gtk.css` before `m3e-gtk4.css`, which uses them.
- `gtk/m3e-gtk3-motion.css`: GTK 3 has no CSS variables, so this file only holds inert `.m3e-spring-<name>` example rules whose
  values are copied by hand into `overrides/m3e-gtk3-motion.css`.

Each curve is a cubic-bezier fitted to the spring response over a 40 px move; the duration is the spring settling time.
