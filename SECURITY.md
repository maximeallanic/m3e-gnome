# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub: *Security* tab, *Report a vulnerability*
(private vulnerability reporting). Do not open a public issue. Include the version (`./install.sh --version`), your
distribution and what an attacker can do. You will get an answer within a week; fixes are released as soon as
they are verified.

## What is in scope

The installer runs as your user and changes only your home directory. These are the things it does that matter for
security, and what we promise about them:

- **No root by default.** `sudo` is used only if you pass `--install-deps` (to run your package manager) or `--gdm`
  (the opt-in login-screen theming), and only after showing the exact command or plan and asking.
- **Pinned and verified downloads.** Git sources are fetched at a full commit and checked; the font and the matugen
  binary are checked against a sha256 before use. A mismatch stops the install.
- **Removal is exact.** `uninstall.sh` removes only the paths recorded in `~/.local/share/m3e-gnome/manifest`,
  refuses any path outside `$HOME`, and never expands a pattern.
- **The GDM helper never runs user-writable code as root.** It is installed root-owned, treats everything the user step
  prepares as untrusted data (no links, size limits, format and CSS allow-list checks), and refuses test hooks as root.
  The model is in [docs/gdm.md](docs/gdm.md); a way around it is exactly the kind of report we want.

Reports about a way to make the installer write outside `$HOME`, run unverified downloaded code, or remove files it
did not create are especially welcome.

## Out of scope

Vulnerabilities in the upstream projects we install (Material-Gnome, Papirus, matugen, GNOME Shell, ...): report them
to those projects. Tell us if a pinned version has a known issue so that we can move the pin.

## Supported versions

Only the latest release.
