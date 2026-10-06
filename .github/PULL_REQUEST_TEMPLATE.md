## What and why

<!-- What does this change, and what problem does it solve? Link the issue if there is one. -->

## How I checked it

<!-- Commands you ran, GNOME version and distribution. For installer changes: tests/run.sh output. -->

## Checklist

- [ ] `tests/run.sh` passes (and the tool tests if I touched `tools/` or `theme/bin`)
- [ ] Code, comments and messages are in English; no language or locale is hard-coded
- [ ] No source file over 500 lines
- [ ] New files created by the installer go through `lib/manifest.sh`; new settings through `gs_set`
- [ ] A new or updated pin is a full commit or a sha256, and `NOTICE.md` / `CHANGELOG.md` are updated
- [ ] I fixed the cause, not the symptom (no swallowed errors, no special cases)
