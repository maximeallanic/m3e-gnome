# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub: *Security* tab, *Report a vulnerability*
(private vulnerability reporting). Do not open a public issue. Include the version (`./install.sh --version`), your
distribution and what an attacker can do. You will get an answer within a week; fixes are released as soon as
they are verified.

## What is in scope

The installer runs as your user and changes only your home directory. These are the things it does that matter for
security, and what we promise about them:

- **No root.** `sudo` is used only if you pass `--install-deps`, only to run your package manager, and only after
  showing the exact command and asking.
- **Pinned and verified downloads.** Git sources are fetched at a full commit and checked; the font and the matugen
  binary are checked against a sha256 before use. A mismatch stops the install.
- **Removal is exact.** `uninstall.sh` removes only the paths recorded in `~/.local/share/m3e-gnome/manifest`,
  refuses any path outside `$HOME`, and never expands a pattern.
- **No login-screen changes.** GDM theming is intentionally not part of this project (the original design ran
  user-writable code as root).

Reports about a way to make the installer write outside `$HOME`, run unverified downloaded code, or remove files it
did not create are especially welcome.

## Out of scope

Vulnerabilities in the upstream projects we install (Material-Gnome, Papirus, matugen, GNOME Shell, ...): report them
to those projects. Tell us if a pinned version has a known issue so that we can move the pin.

## Supported versions

Only the latest release.
