# Contributing

Thanks for helping. This repository is the theme and its installer; the GNOME Shell extensions live in
[m3e-gnome-extensions](https://github.com/maximeallanic/m3e-gnome-extensions).

## Ways to contribute

- **Report a bug** with the issue form. A good report has the version, distribution, GNOME version, session type, steps
  to reproduce and, for a visual problem, a screenshot with no personal data in it.
- **Try it on another setup** (distribution, GNOME version, X11, another app) and report what you saw.
- **Improve the documentation or translate it.** The README and docs are English first; a translation is a new
  `README.<lang>.md` (keep the same structure) linked from the English one.
- **Fix something or add a feature**, as described below. Look at the **good first issue** and **help wanted** labels. Reports that a distribution or GNOME version works (or does not) are valuable: say what you ran and what you saw.

## How to contribute code

1. **Discuss first** for anything beyond a small fix: open an issue (or a Discussion) describing the problem and the
   approach, so that nobody spends time on something that will not be merged. See [GOVERNANCE.md](GOVERNANCE.md).
2. **Fork** the repository and create a branch from `main` named `type/short-description`, where `type` is one of
   `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore` (for example `fix/dock-label-contrast`).
3. **Keep the change focused**: one subject per pull request, no unrelated reformatting.
4. **Run the tests** described below before you push; add or update tests for the behaviour you changed.
5. **Commit with [Conventional Commits](https://www.conventionalcommits.org/)** messages in English
   (`fix(shell): raise contrast of disabled dialog buttons`). The pull request title follows the same format because
   it becomes the squash-commit message.
6. **Open the pull request** against `main`, fill in the template, link the issue (`Fixes #123`) and, for any visual
   change, add before/after screenshots. Never include personal data (names, Wi-Fi networks, file names, e-mails,
   wallpapers you do not have the right to share) in a screenshot.
7. **Review**: a maintainer reviews, usually within a week. Respond to comments by pushing more commits (no force
   push needed: the pull request is squashed). When CI is green and all conversations are resolved, the maintainer
   merges.

By contributing you agree that your work is released under the repository licence (MIT). You are responsible for what
you submit, including anything produced with the help of a tool: read it, run it, and be able to explain it.

What will not be merged: changes that hard-code one language, locale or script; bold text in the theme; steps that
need root outside the explicit opt-ins; unpinned or unverified downloads; files over 500 lines; fixes that hide an
error instead of fixing its cause. These are the design rules of the project; a fork is the place to change them.

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
