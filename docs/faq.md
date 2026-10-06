# FAQ

**Does it need root?** No, not by default. The installer changes only your home directory. `sudo` is used only if you pass
`--install-deps` (your package manager) or `--gdm` (the opt-in login-screen theming, [docs/gdm.md](gdm.md)), after showing
the exact plan or command and asking.

**Which GNOME versions work?** GNOME 50, validated on 50.5. Other versions get a warning and the Shell extensions
will not load (they declare Shell 50 only). See [compatibility](compatibility.md).

**Does it work on X11, Fedora, Arch, Ubuntu?** Untested. Debian was the verified distribution; the package names for
the others are checked as text. Reports are welcome.

**Why do I have to log out?** On Wayland the Shell cannot be restarted in place. The Shell theme, the extensions and
the icon and cursor themes load at login.

**The Shell theme does not apply.** Install the User Themes extension and run `./install.sh` again
([troubleshooting](troubleshooting.md#the-shell-theme-does-not-load)).

**Why is Chrome different?** Chrome only uses the GTK theme when *Appearance > Theme* is GTK, and it keeps a dark
toolbar and active tab in light mode. See [compatibility](compatibility.md).

**Does it theme Qt, Firefox, Flatpak apps, the login screen?** Qt decorations: no. Firefox and Flatpak: untested. The
GDM login screen: yes, opt-in, with a root helper that never runs anything user-writable ([gdm.md](gdm.md)).

**Can I use my own matugen setup alongside?** Yes. This project uses its own config in `~/.config/m3e-gnome/matugen/`
and always passes it with `--config`; `~/.config/matugen/` is never read or replaced.

**Why is matugen only a renderer?** matugen 4.2 implements the 2021 colour spec only. The palette is computed by Google's
material-color-utilities in the 2025 spec, as a current Pixel does. See [architecture](architecture.md).

**Can I pick the colour myself instead of the wallpaper?** Run `material-palette --color "#RRGGBB" --mode dark
--matugen-config ~/.config/m3e-gnome/matugen/config.toml`; the next wallpaper change replaces it
([customisation](customization.md#using-a-fixed-colour)). The `fallback_color` in `palette.json` is used only when no
image can be read.

**Why is there no bold text?** It is a deliberate rule of the theme ([design notes](design-notes.md#no-bold)).

**Why no blur?** It was tried and dropped; surfaces are tinted. Reasons in [design notes](design-notes.md#no-blur).

**Can I install only part of it?** Yes: `--skip gtk-theme|icons|cursor|sounds|font|palette|extensions`, `--no-extensions`,
`--extensions-only`.

**Can I use the extensions without the theme?** Yes, motion still runs but the styling hooks stay empty; see the
[extensions README](https://github.com/maximeallanic/m3e-gnome-extensions).

**Does the live wallpaper (Hanabi) come with it?** No. If you use Hanabi, the palette is taken from the image next to the
video, or a frame of it ([customisation](customization.md#where-the-colours-come-from)).

**Does it use the network?** The installer downloads its pinned sources (GitHub, android.googlesource.com for the pointer drawables, matugen's release) and verifies commits or checksums. The theme and scripts do not need the network once installed; the palette is computed locally.

**How do I remove it?** `./uninstall.sh` ([troubleshooting](troubleshooting.md#uninstall-and-restore)).

**Is the interface translated? What about other languages?** The theme and extensions contain no text, so they follow
whatever language GNOME uses. Installer messages are English.

**Is it affiliated with Google?** No. See the trademark note in [NOTICE.md](../NOTICE.md).
