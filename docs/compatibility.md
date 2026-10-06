# Compatibility

"Verified" means checked by the author on the stated setup (a real session, or the nested headless Shell used by the
benches in `dev/`). Anything else is "untested". The theme is validated on **GNOME Shell 50.5** only.

## Platform

| | Status | Notes |
|---|---|---|
| GNOME Shell 50.5 | Verified | The extensions declare `"shell-version": ["50"]` and patch private Shell classes |
| Other GNOME versions | Untested | The installer warns and continues; the extensions will not load on other Shell versions |
| Wayland session | Verified | Real session and nested headless Shell (1920x1080, 60 Hz, scale 1) |
| X11 session | Untested | |
| Fractional scaling, other refresh rates | Untested | Extension animation cost on real high-refresh or very wide displays was not measured |
| Debian | Verified | The installer's round trip was run on Debian (per CONTRIBUTING: only Debian was run for real; the round-trip test itself uses fake GNOME tools in a temporary home) |
| Ubuntu | Untested | Same package names as Debian |
| Fedora, Arch, openSUSE | Untested | Package names are checked as text only |
| x86_64 | Verified | matugen release binary |
| Other architectures | Unsupported by the installer as is | Build matugen 4.2.0 with cargo first |
| Non-default XDG directories | Unsupported | The matugen config uses `~/.config`, `~/.cache`, `~/.local/share` literally; the installer stops if `XDG_*_HOME` differs |
| Python | 3.9 or newer | The installer checks |

## Applications

| Application | Status | Notes |
|---|---|---|
| GTK 4 / libadwaita apps | Verified on Files (Nautilus), Settings, Calculator, Text Editor and Ptyxis | Restyled through `~/.config/gtk-4.0/gtk.css`; restart apps to pick up a new palette. Several app-specific fixes exist (Files column headers, Settings sidebar rows, Calculator display) |
| GTK 3 apps | Verified on Disks and a GTK 3 test client | Same look with values written out (GTK 3 has no CSS variables) |
| Ptyxis | Verified | `material` palette set on the default profile; active-tab colours with other palettes are a manual step |
| Chrome / Chromium | Verified on Chrome 154 | Needs *Appearance > Theme: GTK*. Toolbar and active tab stay dark in light mode. Page content is not themed. Title-bar buttons are within about 1 px of GTK's |
| Firefox | Untested | |
| Qt applications | Not themed | Qt decorations do not follow the CSS (title bar grey, no shadow). Colours of Qt widgets are not handled by this project |
| Flatpak applications | Untested | The installer does not configure Flatpak, see [installation](installation.md#flatpak-applications) |
| libdecor windows, mutter X11 frames | Partly | Title-bar geometry follows the CSS; shadows and bottom corners are drawn by libdecor or mutter |

## Shell and extensions

| Item | Status |
|---|---|
| Top bar, menus, quick settings, calendar, notifications, overview, app grid, dialogs, OSD, screenshot UI, on-screen keyboard | Verified in the nested Shell bench (dark and light) |
| Lock screen | Styled and checked in a nested Shell; always dark |
| GDM login screen | Not themed, on purpose |
| Dash to Dock | Optional; restyled and its slide animation moved by `m3e-extensions`. The installer sets `apply-custom-theme` to false so the dock takes its surface from the theme |
| GSConnect | Its stylesheet hooks are in the extension stylesheet; behaviour not separately verified |
| Blur my Shell | Conflicts in principle (this theme uses tinted surfaces, no blur); the installer warns when it is enabled |
| Other third-party extensions | Untested; extensions that replace the same Shell methods as `m3e-motion` conflict |

## Quick settings tile titles

At the tile width the theme uses (198 px), some long titles are cut off. In the author's French session these were
"Partage de connexion" (Hotspot), "Mode puissance" (Power Mode) and "Rotation automatique" (Auto Rotate); making them
fit would need tiles about 259 px wide. This is an open decision (see [design notes](design-notes.md#decisions-to-validate)).
Titles are truncated, not overlapped. English titles were not measured.

## Languages

The theme draws no text and assumes no language. The Shell bench and the GTK bench take the locale as a parameter and
check text widths with Latin, CJK and Arabic strings. Only French and English desktops were looked at by eye.
