# Development

Ground rules are in [CONTRIBUTING.md](../CONTRIBUTING.md): English everywhere in code, no file over 500 lines, fix
causes not symptoms, search before you build, pin every external source.

## Repository map

| Path | What |
|---|---|
| `install.sh`, `uninstall.sh`, `verify.sh`, `lib/` | Installer, one concern per file |
| `theme/` | What is installed: `bin`, `icons`, `matugen`, `motion`, `overrides` (GTK and Chrome CSS, templates), `shell` (Shell CSS parts), `systemd` |
| `tools/` | Build-time tools: `material-palette`, `material-symbols`, `googlebook-cursors`, `papirus-symbolic.py` |
| `tests/` | Installer tests |
| `dev/` | Benches and reference data; nothing in it is installed |

## Tests

Installer (no GNOME session needed, nothing leaves a temporary HOME):

```sh
tests/run.sh      # syntax, shellcheck (if installed), file sizes, round trip, guard tests
```

The round trip installs, verifies, reinstalls and uninstalls inside a temporary HOME and requires the home directory to
be byte-identical afterwards. `gsettings`, `dconf`, `gnome-extensions`, `systemctl` and `gnome-shell` are shims over a
fake settings store, and pinned sources are replaced by local git fixtures. Environment knobs: `M3E_TEST_OFFLINE=1`,
`M3E_TEST_NETWORK=1`, `M3E_TEST_NO_MATUGEN=1`, `M3E_TEST_EXTENSIONS_REPO=DIR`, `M3E_TEST_KEEP=1`
(see `tests/run.sh`).

Tools (as in CI):

```sh
for d in theme/bin tools tools/googlebook-cursors tools/material-symbols; do
    (cd "$d" && python3 -m unittest discover -s tests -v)
done
(cd tools/material-palette && npm ci && npm test)
```

What these cannot cover: a real GNOME Shell session (extension loading, live theme reload), other distributions'
package names, non-x86_64 matugen. CI (`.github/workflows/ci.yml`) runs ShellCheck, the installer tests (also once with
the cursor built from AOSP) and the tool tests on Ubuntu with Node 22.

## Static checks and benches (`dev/`)

All write only under their own output directory (`dev/out/`, git-ignored, or `M3E_BENCH_OUT`), never into
`~/.config`, `~/.themes` or the real dconf. Full usage: `dev/README.md`.

```sh
python3 dev/m3e-bench/verify_tokens.py dev/reference/m3e-tokens.json theme/shell/m3e-shell/*.css
python3 dev/m3e-bench/verify_tokens.py dev/reference/m3e-tokens.json theme/overrides/m3e-gtk{3,4}-*.css
python3 dev/m3e-bench/verify_css.py theme/overrides/m3e-gtk3.css theme/overrides/m3e-gtk4.css
python3 dev/m3e-bench-gtk/verify_springs.py
python3 dev/m3e-bench-extensions/verify_sheet.py
python3 dev/m3e-bench/render_theme.py --out /tmp/rendered --mode dark
```

The Shell bench (`dev/m3e-bench-shell/run.sh`) and the GTK bench (`dev/m3e-bench-gtk/run.sh`) render the theme with
matugen into a private directory and capture surfaces and real applications in a nested headless Shell, then compare
with token-derived expectations (about 1 px and a colour difference below 2 on the dE2000 scale). They need the
`m3e-gnome-extensions` checkout (`../m3e-gnome-extensions` or `$M3E_EXTENSIONS_REPO`), whose `nested.sh` owns all the
isolation guards. The animation benches live in the extensions repository (`tests/bench/run.sh --suite
core|motion|extensions`).

Run each bench unit-test file on its own from its `tests/` directory; do not use `unittest discover` there (see
`dev/README.md`).

## Safety rules for nested shells

These come from `dev/README.md` and are strict:

- Never start `gnome-shell` outside `nested.sh`: headless with a virtual monitor, a named Wayland display, a private
  `XDG_RUNTIME_DIR`, every `XDG_*` exported before `dbus-run-session`, logind neutralised. Never `--devkit`, never the
  real `wayland-0`.
- No uinput or key injection into the real session. Never kill `ptyxis` or `gnome-shell` by name: signal only PIDs you
  started.
- Render the theme only into a temporary directory. Delete exact paths, never globs.
- A nested Shell talks to the real system bus: network and VPN tiles show real names in screenshots. Do not publish
  `dev/out/`.
- The locale is always a parameter; text-width checks use Latin, CJK and Arabic strings.
- Exit code 3 means the real dconf changed, 4 that the host runtime directory changed.

## Regenerating generated files

| What | How |
|---|---|
| Palette bundle | `tools/material-palette/build.sh [OUT]` (`npm ci`, then esbuild bundles `palette.mjs`; default `~/.local/lib/material-palette/palette.mjs`). The installer does this itself. |
| Palette settings | `theme/matugen/palette.json` |
| Icon theme | `python3 tools/material-symbols/build.py [--icons-dir DIR]` writes `DIR/Material-Symbols`; `Papirus-Dark` must already be installed in `DIR`. Mappings: `map.py` (status icons) and `map_apps.py` (application icons); knobs `MS_STYLE`, `MS_FILL`, `MS_INK_HEIGHT`, `APP_INSET`. The committed `theme/icons/Material-Symbols` is this output (without the icon cache), plus the hand-drawn window controls |
| Cursor | `python3 tools/googlebook-cursors/build.py black\|white [--icons-dir DIR]` (needs `rsvg-convert`) |
| Papirus-Symbolic | `python3 tools/papirus-symbolic.py ICONS_DIR` (run by the installer) |
| Spring table (`theme/motion/gtk/*.css`) | Generated by the m3e-motion generator of `m3e-gnome-extensions` (`python3 tools/generate.py --check` there); never edit by hand |
| Tokens (`dev/reference/m3e-tokens.json`) | From AndroidX; provenance in `dev/reference/SOURCES.md` |

## Adding or changing Shell CSS

Shell CSS parts are matugen templates in `theme/shell/m3e-shell/NN-*.css`. Declare a new part in
`theme/matugen/config.toml` with the next index, before `shell-99-no-bold`, and add it to the `post_hook` list of that
last part (the hook concatenates them). Keep every matugen `if/else` block inside one file. Every number needs its token
comment or `M3E-visual: <reason>`; run `verify_tokens.py` and `st_sheet.py` (St ignores unknown properties silently).

## Installer rules, in short

Never leave the user's home; `sudo` only for `--install-deps`; create files only through the `put_*` / `record_*`
helpers of `lib/manifest.sh`; set settings only through `gs_set`; guard destructive commands (`rm -rf --
"${var:?}"`); every mutation must honour `--dry-run`. Details in CONTRIBUTING.md.

## Release process

1. Finish the work; `tests/run.sh`, the tool tests and CI must pass.
2. **Pin the extensions.** Set `EXT_REV` in `lib/pins.sh` to the full 40-hex commit of `m3e-gnome-extensions`
   that this version was tested with (normally the commit its own release was tagged on).
3. **Re-check every pin** (`lib/pins.sh`): the commits are fetchable, the sha256 values match, and the new content
   was looked at. `scripts/check-pins.sh` checks the 40-hex format and fetches every git pin (network). Update the
   date comments. Record pin changes in `CHANGELOG.md` and `NOTICE.md`.
4. Bump `M3E_VERSION` in `lib/common.sh`, turn `[Unreleased]` of `CHANGELOG.md` into `[X.Y.Z] - date` (the section
   becomes the release notes), merge.
5. On an up-to-date `main`: `scripts/release.sh X.Y.Z` checks the version, the CHANGELOG section, the `EXT_REV` format, a
   clean tree and a free tag, then prints the tag commands (it runs none). Push the tag `vX.Y.Z`.
6. The *Release* workflow (`.github/workflows/release.yml`) runs the full CI, checks the pins upstream (`EXT_REV`
   included), builds `m3e-gnome_<version>_all.deb` and the source tarball, writes `SHA256SUMS`, attests their
   provenance and creates the GitHub release (a pre-release when the version is below 1.0.0 or has a suffix) with the
   CHANGELOG section plus `.github/release-footer.md` ("Tested on", install, verification) as notes. Running it by hand
   (*Run workflow*, with a version) builds everything and publishes nothing.
7. Screenshots go in `screenshots/` with the names the README references.

### The Debian package

`scripts/build-deb.sh VERSION` (plain `dpkg-deb`: nothing to compile, so debhelper would add only ceremony) packs the
runtime tree under `/usr/share/m3e-gnome` (read-only for users), with the palette bundle prebuilt by
`tools/material-palette/build.sh` so that no npm runs at install time, wrappers in `/usr/bin` (they refuse to run as
root), man pages generated from `--help` (`packaging/mkman.py`) and a bash completion (`packaging/m3e-gnome.bash`, kept
in sync with `--help` by `tests/test_deb.sh`). Maintainer scripts only print. `tests/test_deb.sh` builds it, unpacks it
with `dpkg -x`, makes the tree read-only and runs the round trip from it. The scripts must never write inside their own
directory: build tools work in temporary copies and Python runs with bytecode writing off.

## Pin updates

A pin is a full commit (git sources) or a sha256 (downloads: Google Sans Flex, matugen). To move one: fetch the new
revision, read the diff, change the value and the date comment in `lib/pins.sh`, run `tests/run.sh`
(`M3E_TEST_NO_MATUGEN=1` and `M3E_TEST_NETWORK=1` exercise the real downloads), then update `NOTICE.md` and
`CHANGELOG.md`. Updating Material-Gnome also needs a check that the GTK 4 bold-weight rewrite still applies
(`step_gtk_theme`) and that the base theme's `colors-template.css` is still what `theme/matugen/config.toml` renders.
