# dev/: test benches and reference data

Everything here checks the theme (`theme/`) against Material 3 Expressive references. Nothing here is installed or
shipped. All tools write only under their own output directory (default `dev/out/`, git-ignored; override with
`M3E_BENCH_OUT`), never into `~/.config`, `~/.themes` or the real dconf.

| Path | What it checks / holds |
|---|---|
| `reference/` | `m3e-tokens.json` (M3E tokens from androidx, English schema), `shell-stock/` (stock GNOME Shell 50.5 CSS). See `reference/SOURCES.md`. |
| `m3e-bench/` | Shared harness + static checkers (below). |
| `m3e-bench-shell/` | Shell style bench: surfaces captured in a nested Shell, measured against token-derived expectations. |
| `m3e-bench-gtk/` | GTK 3/4 + libadwaita motion/layout bench with real apps in a nested Shell. |
| `m3e-bench-extensions/` | Static check of `theme/shell/m3e-extensions-template.css`. |
| `screenshots/` | Capture driver for the README screenshots: nested Shell with a fake home, private system bus and audio, generated wallpapers (see its README). |
| `pixel-measure/` | Generic video tools (screen recording -> displacement, activity, spring fit). |

## Static checks (no Shell needed)

```sh
python3 dev/m3e-bench/verify_tokens.py dev/reference/m3e-tokens.json theme/shell/m3e-shell/*.css      # Shell parts
python3 dev/m3e-bench/verify_tokens.py dev/reference/m3e-tokens.json theme/overrides/m3e-gtk{3,4}-*.css
python3 dev/m3e-bench/verify_css.py theme/overrides/m3e-gtk3.css theme/overrides/m3e-gtk4.css        # GTK parses them
python3 dev/m3e-bench-gtk/verify_springs.py                                                          # GTK motion springs
python3 dev/m3e-bench-extensions/verify_sheet.py                                                     # extensions sheet
python3 dev/m3e-bench-shell/st_sheet.py <rendered gnome-shell.css>                                   # St ignores unknown properties silently
python3 dev/m3e-bench/render_theme.py --out /tmp/rendered --mode dark                                # render the theme privately
```

`verify_tokens.py` rules: every number carries its token in a trailing comment (`/* Switch.TrackWidth */`) or
`M3E-visual: <reason>`; colours are matugen expressions; no bold; `!important` only in the no-bold rule, the
flat-surface borders and declarations marked `important-exception: <reason>`.

## Nested-Shell benches

`m3e-bench-shell/run.sh [--batch N] [--surfaces a,b] [--out DIR] [--candidate FILE] [--locale LOC]` and
`m3e-bench-gtk/run.sh [--modes dark,light] [--scenarios client4,client3,ptyxis,files,calculator,settings] [--locale LOC]`.
Both render the theme with matugen into a private directory (`m3e-bench/render_theme.py`: sandboxed copy of
`theme/matugen/config.toml`, no hooks), then start a headless Shell through `nested.sh` of the
`m3e-gnome-extensions` repository (looked up in `../m3e-gnome-extensions`, or `$M3E_EXTENSIONS_REPO`), which owns all
isolation guards. Also read from the environment: `M3E_BASE_THEME` (Material-Gnome base theme, read only, default
`~/.themes/Material-Gnome`), `M3E_BENCH_LOCALE` (default `C.UTF-8`). Exit code 0 = no deviation; 3 / 4 = the real dconf
or the host runtime directory changed (guards of `nested.sh`).

What the Shell bench covers: top bar, menus, quick settings, calendar, notifications, overview/search/app grid,
dialogs, OSD, screenshot UI, keyboard, lock and login (second Shell in gdm mode); light and dark. The GTK bench:
GTK 3/4/libadwaita widgets and Ptyxis/Files/Calculator/Settings with the M3E overrides: no "reported min
width/height" warning, no CSS error, expected sizes held, with Latin + CJK + Arabic labels.
Animation benches (springs, windows, overview, dock, status bar) live in `m3e-gnome-extensions/tests/bench`
(`tests/bench/run.sh --suite core|motion|extensions`) and are not duplicated here.

`m3e-bench/bench.py` (widget grid) opens windows: it only runs inside a nested Shell and refuses otherwise;
`m3e-bench/run.sh --measure DIR` only measures captures already taken (no capture driver exists yet).

## Unit tests

Run each file on its own from its `tests/` directory, e.g. `cd dev/m3e-bench/tests && python3 -m unittest -v test_measure`.
Do not use `unittest discover`. `m3e-bench-shell/tests/test_run.py` has slow cases (real nested Shells) enabled by
`m3e-bench-shell/run.sh --self-test`. `pixel-measure/tests` needs numpy: `uv run --with numpy python -m unittest`.

## Safety rules (strict)

- Never start `gnome-shell` outside `nested.sh`: `--headless --virtual-monitor`, named Wayland display, private
  `XDG_RUNTIME_DIR`, every `XDG_*` exported before `dbus-run-session`, logind neutralised. Never `--devkit`, never
  the real `wayland-0`.
- No uinput / key injection into the real session; never kill `ptyxis` or `gnome-shell` by name: signal only PIDs you started.
- Render the theme only into a temporary directory (never `~/.config`, `~/.themes`); delete exact paths, never globs.
- A nested Shell talks to the real system bus: its network/VPN tiles show real names in screenshots; do not publish `out/`. `screenshots/` is the exception: it gives the Shell a private system bus, audio server and home (still check every image).
- The locale is always a parameter; text-width checks use Latin, CJK and Arabic strings.
