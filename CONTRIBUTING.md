# Contributing

Thanks for helping. This repository is the theme and its installer; the GNOME Shell extensions live in
[m3e-gnome-extensions](https://github.com/maximeallanic/m3e-gnome-extensions).

## Ground rules

- **English everywhere in the code**: identifiers, comments, commit messages, log lines, user-facing strings. Never
  hard-code one human language or locale: tool output that we parse is read with `LC_ALL=C`, and nothing may assume a
  French or English desktop.
- **No source file over 500 lines.** A file that grows towards it holds two responsibilities: split along a real seam.
- **Fix causes, not symptoms.** No retry loop that hides a failure, no `|| true` that swallows an error, no special
  case that makes one test pass. If a fix belongs in another layer, change that layer or say so in the PR.
- **Search before you build**: prefer a maintained dependency to a home-made reimplementation, and say in the PR why
  you adopted or rejected it.
- Every external source is pinned (a full commit for git, a sha256 for downloads). Updating a pin means checking the
  new content, updating `lib/pins.sh` (and the date comment), and noting it in `CHANGELOG.md` and `NOTICE.md`.

## Layout

| Path | What |
|---|---|
| `install.sh`, `uninstall.sh`, `verify.sh` | The three entry points. |
| `lib/` | The installer, one concern per file: `common`, `pins`, `manifest` (ownership), `backup`, `fetch`, `matugen`, `deps`, `settings`, `steps_*`, `verify_checks`, `uninstall`. |
| `theme/` | What gets installed: `bin`, `icons`, `matugen`, `motion`, `overrides`, `shell`, `systemd`. |
| `tools/` | Build-time tools (palette, cursors, icon theme generation). |
| `tests/` | Installer tests (below). |

## Installer rules

1. **Never leave the user's home**, never use `sudo` outside `--install-deps`.
2. **Everything the installer creates goes through `lib/manifest.sh`** (`put_file`, `put_text`, `put_link`,
   `put_tree`, `mkdir_owned`, `record_*`) so that `uninstall.sh` removes exactly those paths. Something that already
   exists and is not ours is moved to `~/.local/share/m3e-gnome/backup/<timestamp>/` first.
3. **Every setting goes through `gs_set`** (it backs the old value up).
4. **Every destructive command is guarded**: `rm -rf -- "${var:?}"`, and uninstall refuses paths outside `$HOME`.
5. `--dry-run` must print the actions and change nothing: new mutating commands go through `run` or the `put_*`
   helpers.

## Tests

```sh
tests/run.sh          # syntax, shellcheck (if installed), file sizes, round trip, guard tests
```

The round trip (`tests/roundtrip.sh`) installs, verifies, reinstalls and uninstalls inside a **temporary HOME** and
checks that the home directory is byte-identical afterwards. gsettings, dconf, gnome-extensions, systemctl and
gnome-shell are shims (`tests/shims/`) over a fake settings store, so a test never touches your session. Pinned
sources are replaced by local git fixtures (`tests/fixtures.sh`, through `M3E_PINS_FILE`). Run it from a terminal
inside your real session safely: nothing leaks (`tests/lib.sh` aborts if a real `gsettings` could be reached).

Environment knobs: `M3E_TEST_OFFLINE=1` (stub `npm ci`; needs `tools/material-palette/node_modules`),
`M3E_TEST_NETWORK=1` (also build the cursor from AOSP), `M3E_TEST_NO_MATUGEN=1` (exercise the pinned matugen
download), `M3E_TEST_EXTENSIONS_REPO=DIR` (also install from a real extensions checkout), `M3E_TEST_KEEP=1` (keep the
temporary directory). Tool tests: `python3 -m unittest discover -s tests` in `theme/bin`, `tools`,
`tools/googlebook-cursors`, `tools/material-symbols`; `npm ci && npm test` in `tools/material-palette`.

What the tests cannot cover: a real GNOME Shell session (extension loading, the live theme reload), other
distributions' package names (only Debian was run for real; the others are checked as text), non-x86_64 matugen.

## Pull requests

Describe what changed and how you checked it, mention the GNOME version and distribution you ran on, and keep the
change focused. CI runs the same tests as above.
