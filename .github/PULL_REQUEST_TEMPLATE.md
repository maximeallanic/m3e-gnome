## What and why

<!-- What does this change, and what problem does it solve? -->

Fixes #

## Type of change

<!-- feat / fix / docs / refactor / test / ci / chore. The PR title must be a Conventional Commit, e.g. "fix(shell): ..." -->

## How I checked it

<!-- Commands you ran, GNOME version, distribution, session type (Wayland/X11). -->

## Screenshots (visual changes)

<!-- Before / after. No personal data: names, Wi-Fi networks, file names, e-mails, private wallpapers. -->

## Checklist

- [ ] `tests/run.sh` passes (and the tool tests if I touched `tools/` or `theme/bin`)
- [ ] New files created by the installer go through `lib/manifest.sh`; new settings through `gs_set`
- [ ] A new or updated pin is a full commit or a sha256, and `NOTICE.md` / `CHANGELOG.md` are updated
- [ ] Code, comments and messages are in English; no language, locale or script is hard-coded
- [ ] No source file over 500 lines
- [ ] I fixed the cause, not the symptom (no swallowed errors, no special cases)
- [ ] I read [CONTRIBUTING.md](CONTRIBUTING.md) and the PR title is a Conventional Commit
