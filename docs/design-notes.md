# Design notes

The reasoning behind the choices that are not obvious from the code. It is condensed from the project's private
working notes (written in French and not published); numbers come from the sources they cite in the code.

## Goal

Material 3 Expressive on the GNOME desktop: the look of an Android 16+ phone (a Pixel was the reference device), at
desktop density, with GNOME's structure kept. Constraint: **extensions and CSS only**. Nothing is recompiled, so
every limit of St (the Shell's toolkit) and GTK's CSS is a limit of the theme.

## Colour

- **Material 2025 colour spec, standard contrast.** matugen 4.2 only implements the 2021 spec and has no phone
  platform, so it gives different roles from a current Pixel (for example `on_primary` white instead of a tinted
  colour). `material-palette` therefore uses Google's `@material/material-color-utilities` directly and matugen only
  renders templates. With the Pixel's seed `#7B9F1C` at contrast 1.0 the library reproduces the phone's system colours
  byte for byte (`primary #1c2800`, `on_primary #cee29d`, `surface_container #eeefe1`); that case is a unit test
  (`tools/material-palette`).
- **Seed extracted like Android** (`WallpaperColors`: image reduced to about 112 x 112 px of area, Celebi quantizer
  with 128 colours, scoring), not matugen's "saturation" preference. On the author's wallpaper this gave a different
  seed (`#74918c` before, `#113744` after).
- **Standard contrast.** The reference phone ran at high contrast, which makes light-mode primaries nearly black.
  The theme does not copy it.
- Extra roles from Android's SystemUI (`surface_effect_0` to `3`) are computed too and used for tiles and notification
  cards.
- Terminal ANSI colours are built the matugen way (a scheme built on the harmonised colour) in the 2025 spec.

## Components

Every number in the stylesheets cites a Material 3 token (`dev/reference/m3e-tokens.json`, from AndroidX) or an
`M3E-visual: <reason>` comment, checked by `dev/m3e-bench/verify_tokens.py`. Components and where they apply are in the
files themselves; some highlights:

- Quick settings tiles: pill when off, rounded rectangle (radius about one third of the height) when on; 56 px height.
- Notifications: "welded" cards as on the Pixel, with large outer radii at the ends of a list and small ones at the
  joints. St cannot tell which message is first or last, so `m3e-motion` sets `:m3e-first` / `:m3e-last`; without it all
  cards get the small joint radius.
- Sliders: split track, bar handle (4 px wide), drawn in JavaScript by `m3e-motion` because St cannot draw it.
- Switches: icon in the thumb, thumb large in both states; the Shell thumb size is set inline by the extension.
- Dialogs: `surface_bright`, 28 radius, pill buttons. OSD: `surface` pill. Calendar: round day cells.
- Title bars: one geometry everywhere, set to match Chrome, whose bar height and button spacing are fixed in its code:
  40 px bar, 30 px round buttons, 16 px glyphs, 6 px gap. Window buttons are hand-drawn icons. Inactive windows show
  their title-bar content at 50 %.

## Motion: springs

Motion is driven by physical springs, not fixed durations (except where Android itself uses a curve). Values are the six
Compose `MotionScheme.expressive` springs (stiffness / damping ratio, mass 1):

| Spring | Stiffness | Damping | Used for |
|---|---|---|---|
| DefaultSpatial | 380 | 0.8 | position, size, radius |
| FastSpatial | 800 | 0.6 | same, snappier |
| SlowSpatial | 200 | 0.8 | same, broader |
| DefaultEffects | 1600 | 1.0 | opacity, colour |
| FastEffects | 3800 | 1.0 | same, snappier |
| SlowEffects | 800 | 1.0 | same, slower |

Spatial properties get the first three, effects the last three. A spring's duration depends on the distance travelled
(it is the Compose settling-time estimate), and the visibility thresholds are Compose's. Animations are interruptible
and keep position and velocity when retargeted. Additional Android values (shade expansion fitted from a screen
recording at 0.925 damping, stiffness 197; notification and volume springs) come from pinned Android source files; the
values in the generator data each record their origin.

GTK has no spring engine, so each spring is approximated by a cubic-bezier fitted to the spring response over a 40 px
move, with the spring's settling time as duration (`theme/motion/gtk/`, generated). In GTK 4 these are
`--m3e-spring-*` variables; GTK 3 has no CSS variables, so the values are written out. Shape morphs use pixel radii
(for example 20) instead of `9999px`, because GTK interpolates the radius value and a huge radius stays "full" until the
very end of the animation.

Shell choreographies (`m3e-motion`): container transform for opening an app from its icon and for minimise/restore,
Android activity-open slide for windows without a source, fade for dialogs, spring-driven overview, banners that slide,
quick-settings shade that opens by content moving down.

Things the Shell's GTK-side cannot do and that were removed or left alone: the overscroll halo is removed (GTK draws or
erases it frame by frame with no state to delay; Android and M3 stretch content instead), Material-Gnome's "pop"
bounce keyframes on buttons, tabs, rows and check marks are neutralised, and hard-coded libadwaita animations
(navigation view, dialogs, tab widths, switch) stay as they are.

## Pixel alignment decisions

The look was compared with a Pixel 10 Pro (Android 17) measured over adb. Decisions that came out of it:

- **Style and motion only.** GNOME's structure stays: two-column quick settings, horizontal OSD, calendar plus
  notifications. The Android layout is not copied.
- **Android proportions at desktop density.** Lengths are multiplied by 56/72 (a 72 dp tile becomes 56 px); ratios are
  kept (active tile radius is one third of the height, inactive is a pill, 28/4 for group ends and joints).
- **Colours follow the 2025 spec at standard contrast**, not the phone's high-contrast setting.
- **No bold.** The phone uses Medium weight for titles; the theme sets everything to 400, deliberately.
- Android's vertical volume panel, its tile grid and its notification-shade layout are not reproduced.

## No blur

Blur was tried and dropped (decision of the maintainer, 2026-10-04): surfaces are **tinted** instead. On GNOME 50 mutter
offers extensions no blur API that works with rounded corners: `Shell.BlurEffect` has no rounded corners, and dynamic
blur from an extension runs into mutter's culling, partial redraws, off-screen rendering (Dash to Dock, BoxPointer) and
the overview's clones, plus rebuilding a patched library on each mutter update. The top bar and dock are tinted
`surface_container` at 85 %, menus are opaque. Mutter 51's `ext-background-effect-v1` protocol lets an application ask
for blur, but does not cover the Shell's own interface. This is why the installer warns if Blur my Shell is enabled.

## No bold

A strict visual rule of the theme: no `font-weight` above 400 anywhere (GTK 3, GTK 4, Shell), because the interface
font is a variable font and the look is flat and light. How it is enforced is in [customisation](customization.md#the-no-bold-rule).

## Density

Desktop density rather than phone density: 14 px body text, 40 px title bar, 36 px top bar (so Extra-small 32 dp
buttons rather than Small 40 dp, which do not fit), 56 px tiles. Mouse-sized targets, tinted surfaces and pills are
kept.

## Why Shell CSS is concatenated, and other St facts

- A single stylesheet built by concatenation: `@import` in St has lower priority, which broke menu colours.
- St orders by stylesheet first and specificity second; a theme rule beats the stock rule, but the stock `!important`
  survives and only a theme `!important` beats it (allowed only for unreadable text, one declaration, with a reason).
  Extension stylesheets (`St.Theme.load_stylesheet`) beat the theme even against `!important`.
- St ignores unknown properties silently; one shadow only; one background; no `calc()`; no percentage lengths; no
  `spacing` on widgets with a Clutter layout manager; negative margins read as unsigned (they crash the Shell on an
  icon); `border-radius` is not interpolated. The status-bar extension therefore uses its own layout manager.
  `dev/m3e-bench-shell/st_sheet.py` rejects what St would ignore.

## Language and ownership

The theme draws no text of its own and the extensions have no user-interface strings, so nothing is tied to a language.
Percentages use `Intl.NumberFormat`; the drawing code handles right-to-left; installer messages are English and the
tools that parse system output read it with `LC_ALL=C`. The benches take the locale as a parameter and check text
widths with Latin, CJK and Arabic samples. Nothing is translated. Ownership: this repository and its companion are MIT
licensed and maintained by Maxime Allanic; third-party parts keep their licences ([NOTICE.md](../NOTICE.md)).

## Decisions to validate

These were made autonomously during development and are open to the maintainer's review:

1. **Quick settings tile width.** Tiles are 198 px; a few long titles are truncated. Options: 259 px tiles, or shorter
   titles. Unchanged.
2. **Window close.** A closing window fades out instead of returning to its dock icon (return is reserved for minimise).
3. **Windows without a source** fade (dialogs) or slide in (normal windows) rather than expanding.
4. **Overview** is the Shell's layout driven by a spring, with clamped state.
5. **Shade distances** (164 dp open, 177 dp close, cut at 150 dp) were fitted to one recording of one phone.
6. **Window corner radius** is a constant 12 px; an application drawing other corners shows a slight seam at the end.
7. **Launch source window.** The icon a launch came from is remembered for 8 seconds; an already-running app that opens
   a window by itself in that time also starts from the icon.
8. **Not handled:** lock-screen motion, dimming of the parent under dialogs, calendar page cross-fade, multi-page folders,
   search-result appearance.
9. **Open measurements:** animation cost on high-refresh and very wide displays (the benches run at 60 Hz, headless).
