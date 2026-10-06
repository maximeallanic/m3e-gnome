# GDM login screen (opt-in)

`./install.sh --gdm` gives the GDM login screen the M3E-Shell dark sheet, the Material-Symbols icons, the Googlebook
cursor, Google Sans Flex and (when your wallpaper is a plain image) a blurred copy of it as background. It is the only
part of this project that uses root, it is never part of the default path, and it is built so that **nothing the user can
write is ever run, sourced or followed by root**.

![Login screen, password prompt, dark](../screenshots/login-dark.png)

*A nested GNOME Shell in `gdm` mode, rendered with the same stylesheet the helper installs. Demo user, no wallpaper (the
capture has none, so the background is the flat surface colour). The lock screen could not be captured faithfully: the
bench draws a magenta probe rectangle on it.*

## Contents

- [What it changes on the system](#what-it-changes-on-the-system) / [Security model](#security-model-and-threat-model)
- [Mechanism and per-distribution status](#mechanism-and-per-distribution-status)
- [Install, update, uninstall](#install-update-uninstall) / [Recovery](#recovery-from-a-tty) / [FAQ](#faq)

## What it changes on the system

Everything below is recorded, with its previous state, in `/var/lib/m3e-gnome/gdm/manifest`. `./uninstall.sh --gdm`
(or `sudo m3e-gdm restore`) removes exactly these paths and restores what was replaced.

| Path | What |
|---|---|
| `/usr/local/libexec/m3e-gnome/gdm/` (root-owned, 0755, files 0644/0755) and the link `/usr/local/sbin/m3e-gdm` | The helper. Copied from your checkout at install time; never run from `$HOME` or the git checkout |
| `/var/lib/m3e-gnome/gdm/` | State: `manifest`, `mech`, `data/` (the validated copy of the data), `data.sha256`, `stock.sha256`, `built.sha256`, backups |
| the stock gresource, by mechanism | see [below](#mechanism-and-per-distribution-status) |
| `/usr/local/share/icons/Material-Symbols`, `/usr/local/share/icons/Googlebook` (or `-White`), `/usr/local/share/fonts/GoogleSansFlex` | The greeter runs as the `gdm` user and cannot see your home |
| `/usr/local/share/m3e-gnome/gdm/background.png` | The blurred wallpaper |
| `/etc/dconf/profile/gdm`, `/etc/dconf/db/m3e-gdm.d/00-m3e-gdm`, `/etc/dconf/db/m3e-gdm` | Greeter settings (icon theme, cursor, font, dark scheme). Our database is added to the `gdm` profile after `user-db:`; the distribution's lines are kept. A pre-existing `/etc/dconf/profile/gdm` is backed up |
| `/etc/apt/apt.conf.d/99m3e-gdm`, or `/etc/pacman.d/hooks/m3e-gdm.hook`, or the DNF action files | Rebuild hook after package updates |

The Debian dpkg database is touched through `dpkg-divert` only (it keeps `diversions-old`, as dpkg always does).

## Security model and threat model

The old private script (`theme-gdm.sh`) ran as root and `exec`-ed `~/.local/bin/theme-sync` and read files from `$HOME`:
any process running as the user could get root the next time the owner ran it, or when the package hook ran. The
rebuild keeps the feature and removes that class of problem.

In plain words:

1. **Root only for this step**, through `sudo`, after the installer prints the exact plan (it runs the helper in
   `--dry-run` as your own user to compute it) and asks. `--yes` skips the question, `--dry-run` never calls `sudo`.
2. **The helper is root-owned code.** It is installed with `install` into a root-owned directory and checks, every time it
   starts, that the directory and every file in it are owned by root and not group- or world-writable and are not
   symbolic links. It refuses otherwise. Run from your checkout as root, it refuses (the checkout is yours).
3. **User input is data, not code.** The user step (as your user) renders the stylesheet from the repository templates
   with the seed you chose, blurs the wallpaper with ffmpeg, and copies the icon, cursor and font files into a private
   temporary directory. The helper reads that directory with `ingest.py` (Python standard library, `python3 -I`):
   - every entry is opened with `O_NOFOLLOW` relative to its parent directory; symbolic links, hard-linked files, FIFOs
     and devices, and world-writable entries are refused;
   - size limits: stylesheet 3 MiB, PNG 24 MiB and 8192 px per side (magic, IHDR checksum and IEND checked), assets
     8 MiB per file and 64 MiB in total, at most 6000 files; names from a restricted alphabet; extensions from an
     allow-list; cursor files must start with `Xcur`, fonts with a font magic, SVG with no external `href`;
   - the stylesheet must be UTF-8 without NUL, with no backslash escape (they can hide `url(` or `@import`), no `@import`,
     and every `url()` must be `resource:///org/gnome/shell/theme/<name>.svg|png` or the staged background;
   - `greeter.conf` accepts four keys and values without quotes, brackets, `$`, `;` or control characters.
   What passes is **copied** (not moved) into the root-owned `/var/lib/m3e-gnome/gdm/data`; only that copy is used from
   then on, so editing your directory later changes nothing (a test checks it), and the package hooks need no user
   session.
4. **The resource is built in a root-owned temporary directory** from the stock resource plus the staged sheet with
   `glib-compile-resources`, then verified before it is used: same resource list as the stock one, every non-stylesheet
   resource byte-identical, the stock sheets preserved at the start of both CSS files, the staged sheet found verbatim
   after the marker. It replaces the live file by rename (atomic): GDM never sees a missing or half-written resource.
5. **Test hooks cannot be used to redirect a real root run.** The helper can be pointed at a fake root only with
   `M3E_GDM_TEST=1` plus `M3E_GDM_ROOT`, and **only when the effective uid is not 0**; as root, the mere presence of
   either variable is a fatal error. As root it also resets `PATH` and drops `BASH_ENV`, `LD_*`, `PYTHON*`, `TMPDIR`, ...
6. Removal is by manifest, through an allow-list of path prefixes; no path is removed by pattern.

What it does not protect against: a root-level attacker (they own the machine anyway), a compromised package in the
repository you installed from, and you running `sudo` on something else. The copy of the helper into
`/usr/local/libexec` reads files from your checkout as root (`sudo install`), exactly like `sudo make install`: review
what you install, as always.

Tested (see `tests/test_gdm_input.sh`): symlinked, oversized, non-PNG, absurd-dimension and truncated inputs; CSS with
`@import`, network URLs, `file:` URLs, escaped `url(`, NUL, invalid UTF-8, unrendered placeholders; hard links, FIFOs,
world-writable files and directories, unexpected entries; hostile `greeter.conf`; each refusal leaves the fake system
byte-identical; test hooks refused as (simulated) root; helper directories that are not root-owned, group/world-writable
or contain a link are refused.

## Mechanism and per-distribution status

How the greeter's `gnome-shell-theme.gresource` is replaced. Researched on this machine (Debian forky, GNOME Shell and
GDM 50: no `gdm-theme.gresource` alternative exists, the resource is a plain file of `gnome-shell-common`) and in the
documentation and issues of other distributions. We **adopt** the known approach of
[gdm-settings](https://github.com/gdm-settings/gdm-settings) (extract the stock gresource, add the stylesheet, recompile;
settings through `/etc/dconf/db/gdm.d`-style databases) and **build** the rest: its privileged part is a GUI app
running as the user through polkit, which is not the boundary we want.

| Family | Mechanism | Refresh hook | Status |
|---|---|---|---|
| Debian (forky/sid) | `dpkg-divert` (no rename, atomic swap): stock file kept as `.distrib`, updates write there | `/etc/apt/apt.conf.d/99m3e-gdm` (`DPkg::Post-Invoke`) | **Verified** in a fake root with the real `dpkg-divert` and in a nested Shell; **not yet on a real boot** |
| Ubuntu | `update-alternatives` `gdm-theme.gresource` (our file added as a priority-900 candidate and selected; package files untouched; falls back to `gdm3-theme.gresource`) | apt hook | Alternative handling verified with the real `update-alternatives` in a fake root; **untested on a real Ubuntu** (the alternative layout is from [reports](https://github.com/vinceliuice/MacTahoe-gtk-theme/issues/148), not from a running system) |
| Arch | In place: stock bytes kept in `/var/lib/m3e-gnome/gdm/stock/`; a package update overwrites the file and the hook rebuilds from the new stock | `/etc/pacman.d/hooks/m3e-gdm.hook` (`PostTransaction`, `Target = gnome-shell`; syntax from [alpm-hooks(5)](https://man.archlinux.org/man/alpm-hooks.5)) | In-place logic **verified** in a fake root; the hook file is only checked as text. **Untested on real Arch** |
| Fedora | In place (as Arch) | DNF 4 `post-transaction-actions.d/m3e-gdm.action` and DNF 5 `libdnf5-plugins/actions.d/m3e-gdm.actions` (syntax from the [DNF 4](https://dnf-plugins-core.readthedocs.io/en/latest/post-transaction-actions.html) and [DNF 5](https://dnf5.readthedocs.io/en/latest/libdnf5_plugins/actions.8.html) docs); written only when the plugin's directory exists, otherwise a warning | In-place logic **verified** in a fake root; hooks only checked as text. **Untested on real Fedora**; `rpm-ostree` systems are not supported |
| openSUSE | In place | none yet | **Not supported for updates: needs a contributor.** What is missing: a zypp commit plugin or a `zypper ps`-time hook that runs `m3e-gdm refresh` after `gnome-shell` changes. Until then run `sudo m3e-gdm refresh` after each gnome-shell update |
| Others | In place, no hook | none | Same as openSUSE |

On Debian and in-place systems the stock resource is **shared** by the greeter and by your own session (GNOME Shell loads
the same file; the user theme is loaded on top). The login sheet therefore also becomes the base sheet of a session whose
Shell theme is not M3E-Shell. The installer warns when your Shell theme is not M3E-Shell. Ubuntu's alternative does not
have this limit.

GNOME Shell major: the helper was verified with **50**. `apply` refuses another major without `--force` (`--gdm-force` on
the installer). When a package update brings another major, `refresh` puts the stock sheet back in service and warns
instead of building against a layout nobody checked.

## Install, update, uninstall

```sh
./install.sh --gdm            # after a normal install; prints the plan, asks, then uses sudo for this step only
./install.sh --gdm-only       # only this step
./install.sh --gdm --dry-run  # renders and verifies in temporary files, shows the plan, never calls sudo
./install.sh --gdm-image ~/Pictures/wall.png     # seed colour and background
./verify.sh                   # includes a read-only GDM section when it is installed (exit status non-zero on a mismatch)
./uninstall.sh --gdm          # revert only this part (sudo, plan shown first); the full ./uninstall.sh does it too
```

The colours are **frozen** at install time (the sheet is rendered once, dark palette, from the chosen seed). To change the
seed or the wallpaper background, run `./install.sh --gdm-only` again (idempotent: a second run leaves the system
byte-identical when nothing changed). After a gnome-shell package update the hook runs `m3e-gdm refresh` by itself;
`./verify.sh` tells you if it did not.

## Recovery from a TTY

If the login screen is broken or you want the stock one back, switch to a text console (Ctrl+Alt+F3) and log in:

```sh
sudo m3e-gdm restore                 # exact undo from the manifest
sudo apt reinstall gnome-shell-common   # Debian/Ubuntu: stock resource from the package, whatever our state
# Fedora: sudo dnf reinstall gnome-shell     Arch: sudo pacman -S gnome-shell
sudo systemctl restart gdm           # (from the TTY; this ends graphical sessions)
```

`dpkg-divert` leftover (Debian) if the helper is gone: `sudo dpkg-divert --remove --no-rename --package m3e-gnome
/usr/share/gnome-shell/gnome-shell-theme.gresource && sudo mv /usr/share/gnome-shell/gnome-shell-theme.gresource.distrib
/usr/share/gnome-shell/gnome-shell-theme.gresource`. On Ubuntu: `sudo update-alternatives --remove gdm-theme.gresource
/usr/local/share/m3e-gnome/gdm/gdm-theme.gresource`. The helper never replaces the file in place: if something fails before
the final rename, the previous resource is still there.

## FAQ

**The login screen did not change.** It is read when GDM starts: reboot, or `sudo systemctl restart gdm`. **The second
ends your graphical session and every unsaved document in it: save first.** Then `./verify.sh`; if the mechanism line or the
"live resource" line fails, run `sudo m3e-gdm refresh`. Check also that `gnome-shell --version` is 50.

**The login screen is unthemed after an update.** The package replaced the resource and the hook did not run (or your
distribution has none): `sudo m3e-gdm refresh`.

**Is my wallpaper used?** Only a plain image (`png jpg webp bmp`) set as `picture-uri-dark`; XML, SVG and video wallpapers
fall back to the seed colour and a flat background. Blurred with ffmpeg (1920 px wide, Gaussian sigma 30).

**Languages.** The helper prints English only and parses tool output under `LC_ALL=C`; paths with spaces or non-ASCII
characters work (the tests use a home with spaces). Font names may contain any character except quotes, brackets and shell
metacharacters.

**I used the old private `theme-gdm` script.** Remove its diversion first (`sudo /usr/local/sbin/theme-gdm --restore`): the
helper refuses to take over a diversion made by another package.
