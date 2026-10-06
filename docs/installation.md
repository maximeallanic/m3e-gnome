# Installation

The installer runs as your user and changes only your home directory, unless you ask otherwise: `sudo` is used only for
`--install-deps` and for the opt-in `--gdm` login-screen theming ([gdm.md](gdm.md)). It is idempotent and reversible with
`./uninstall.sh`.

## 1. Dependencies

`./install.sh` detects what is missing for the steps you selected and prints the exact command for your distribution
(from `/etc/os-release` `ID` / `ID_LIKE`). Python 3.9 or newer is required (Debian 11+, Ubuntu 22.04+, current Fedora,
Arch and openSUSE Leap 15.5+ qualify).

The full list (the installer prints only what is missing):

| Family | Status | Command |
|---|---|---|
| Debian / Ubuntu | Debian verified; Ubuntu untested | `sudo apt-get install --no-install-recommends coreutils curl dconf-cli ffmpeg fontconfig git gnome-shell libglib2.0-bin librsvg2-bin meson ninja-build nodejs npm python3 rsync` |
| Fedora | Package names checked as text; untested | `sudo dnf install coreutils curl dconf ffmpeg-free fontconfig git glib2 gnome-shell librsvg2-tools meson ninja-build nodejs npm python3 rsync` |
| Arch | Package names checked as text; untested | `sudo pacman -S --needed coreutils curl dconf ffmpeg fontconfig git glib2 gnome-shell librsvg meson ninja nodejs npm python3 rsync` |
| openSUSE | Package names checked as text; untested | `sudo zypper install coreutils curl dconf ffmpeg fontconfig git glib2-tools gnome-shell meson ninja nodejs-default npm-default python3 rsvg-convert rsync` |

Which tool is needed by which step:

| Step | Needs |
|---|---|
| always | `git curl python3 sha256sum gsettings dconf gnome-extensions` |
| `gtk-theme`, `icons`, `extensions` | `rsync` |
| `cursor` | `rsvg-convert` |
| `sounds` | `meson ninja` |
| `font` | `fc-cache` |
| `palette` | `node npm ffmpeg` |

`gtk-update-icon-cache` (`libgtk-3-bin` on Debian) is optional: without it the icon themes work but GTK applications
start more slowly, and the installer warns.

Any other distribution: install the packages that provide the commands above. matugen is installed by the installer
(see below).

### User Themes extension

GNOME Shell only loads a Shell theme through the **User Themes** extension. If it is missing, the installer warns,
installs everything else, and tells you the command; install it and run `./install.sh` again.

| Family | Package |
|---|---|
| Debian, Ubuntu, Arch | `gnome-shell-extensions` |
| Fedora, openSUSE | `gnome-shell-extension-user-theme` |

### matugen

The installer uses a matugen 4.x already on your `PATH` (4.2.0 or newer, same major). Otherwise it downloads the
pinned release 4.2.0, checks its sha256 and installs it to `~/.local/bin/matugen`. Release binaries exist for x86_64
only; elsewhere run `cargo install matugen --version 4.2.0 --locked` first.

## 2. Install

Run it from a terminal inside your GNOME session:

```sh
git clone https://github.com/maximeallanic/m3e-gnome
cd m3e-gnome
./install.sh --dry-run
./install.sh
```

The installer refuses to run outside a GNOME session (`--no-session-check` overrides this for packaging). On a GNOME
version other than 50 it warns and continues.

Options are listed in the [README](../README.md#install) and in `./install.sh --help`. Examples:

```sh
./install.sh --light --cursor white     # light colour scheme, white pointer
./install.sh --skip sounds --skip font  # keep your sound theme and font
./install.sh --no-extensions            # theme only, no Shell extensions
./install.sh --extensions-only          # only the extensions (also: --extensions-dir ../m3e-gnome-extensions)
./install.sh --install-deps -y          # install missing packages with sudo without asking
```

Steps, in order: `gtk-theme`, `icons`, `cursor`, `sounds`, `font`, `palette` (matugen, templates, scripts, user
service, first palette, Ptyxis palette), then GNOME settings, then `extensions`.

The extensions are fetched from the `m3e-gnome-extensions` repository (built with its `scripts/install.sh`) and copied
to `~/.local/share/gnome-shell/extensions/`. Until the first release pins a commit, they are fetched from the default
branch, with a warning (a branch cannot be verified).

## 3. Log out and back in

Required. The Shell cannot be restarted in place on Wayland; it loads the new Shell theme, the new extensions and the
icon and cursor themes at login, and GTK applications read the new stylesheets when they start.

After logging back in:

```sh
./verify.sh            # read-only: files, rendered outputs, settings, extensions, service
./verify.sh --strict   # warnings (e.g. an extension the Shell has not loaded yet) count as failures
```

`verify.sh` takes the same `--skip`, `--no-extensions`, `--extensions-only` and `--cursor` options, so you can verify
what you installed, and `--no-service` if you do not want the palette service required.

## 4. Chrome and Chromium

Chrome reads the GTK 4 theme only when *Settings > Appearance > Theme* is set to **GTK**. Choose it once, then restart
Chrome.

## Flatpak applications

The theme reaches applications through three paths: the GTK theme name in GNOME settings, user stylesheets in
`~/.config/gtk-3.0` and `~/.config/gtk-4.0`, and icon and cursor themes in `~/.local/share/icons`. The installer does
**not** configure Flatpak (no `flatpak override`, no portal setting), and it was not tested with Flatpak applications.
A sandboxed application sees these directories only if it is given access to them. Treat Flatpak as unsupported until
tested.

## Updating and removing

```sh
git pull && ./install.sh     # update; idempotent
./uninstall.sh               # remove everything and restore the previous state
```

See [troubleshooting](troubleshooting.md#uninstall-and-restore) for how restoration works.
