# dev/screenshots: README screenshots

Reproducible captures of the theme for `screenshots/`. A headless GNOME Shell (through `nested.sh` of the
`m3e-gnome-extensions` repository, like the other benches) runs a staged copy of the theme and of the extensions; a small
extension drives it (virtual pointer and keyboard, window placement, Shell surfaces, `Shell.Screenshot`).

```sh
dev/screenshots/setup.sh                                   # venv: PyGObject and dbus-python from the system, python-dbusmock and Pillow from PyPI
dev/screenshots/make-screenshots.sh [--work DIR] [--out DIR]   # everything, about 4 minutes
dev/screenshots/capture.sh --out /tmp/shots --modes dark --scenarios shell   # raw captures only
```

Requirements: `uv`, `python3-dbus`, `python3-gi`, `pipewire` + `pipewire-pulse`, `dbus-daemon`, `matugen`, the installed
base theme `~/.themes/Material-Gnome`, the Papirus icons, Google Sans Flex and Adwaita Mono (what `install.sh` puts under
`~/.local/share`; `stage.py --icons-src/--font-dir/--mono-font-dir` point elsewhere), GNOME Settings, Files, Ptyxis, and the
`m3e-gnome-extensions` checkout next to this repository (or `$M3E_EXTENSIONS_REPO`). Read only: none of them is modified.

| File | Role |
|---|---|
| `capture.sh` | Orchestrator: private system bus and audio server, then `stage.py` and `nested.sh` per mode. Checks that the real dconf database did not change. |
| `stage.py`, `demohome.py` | Everything built outside the nested Shell: theme render (`render_theme.py`, seed of the wallpaper), GTK 3/4 stacks (`m3e-bench-gtk/stage.py`), icons, fonts, demo home, application list, dconf keyfile, extensions (`scripts/install.sh --dest`). |
| `wallpapers.py` | Generated wallpapers (CC0) and their pinned seed colours. |
| `sysbus.py` | Private system bus with python-dbusmock services: login1, polkit, UPower (battery), NetworkManager (Wi-Fi), BlueZ, power profiles. |
| `audio.py` | Private PipeWire + pipewire-pulse with one fake output; `PULSE_SERVER` points the Shell at it. |
| `m3e-shots@maximeallanic.github.io/` | The driver extension (loads the Shell theme like user-theme, stages the config overlay, exposes the D-Bus API). |
| `shots.py` | Scenarios (`apps`, `shell`, `palette`, `notify`) played inside the nested session through that API. |
| `compose.py` | Crops, the status-bar zoom, the palette montage, PNG optimisation. |

## What keeps real data out of the images

- `HOME` is `<out>/<mode>/home/demo`, `USER=demo`; the application grid only shows an allow-list of launchers (the other
  system ones are masked with `Hidden=true`, the rest are invented launchers that run `true`); `XDG_DATA_DIRS` lists the
  staged directory and `/usr/share` only.
- The system bus the Shell sees (`DBUS_SYSTEM_BUS_ADDRESS`) is private and populated with fake hardware; the audio
  server (`PULSE_SERVER`) is private. `nested.sh` itself keeps `PIPEWIRE_RUNTIME_DIR`/`PULSE_RUNTIME_PATH` of the host, but
  `PULSE_SERVER` takes precedence in libpulse.
- Windows come from applications started by `shots.py` (killed by process group of the PID started, never by name); the
  Settings window is cut above its wallpaper thumbnails and never shows About.
- Still to do by hand after each run: look at every image. `capture.sh` cannot know that a new Settings page shows a host name.

## Known limits

- Lock screen, login screen and night-light/brightness tiles are not captured (logind is faked; brightness needs a monitor
  with a backlight; the lock screen needs the real GDM).
- The notification list uses application names that match no launcher: with a launcher name (`org.gnome.Nautilus`,
  `org.gnome.Software`) the nested Shell dropped the notification. The cause is not established.
- The light session sets `color-scheme` to `prefer-light`: with `default` (what `install.sh --light` sets) GNOME Shell 50
  loads its dark stock sheet under the light palette (calendar month label white on a light card).
- `stage.py --stock-gtk` renders without the GTK user stylesheet, to tell a theme defect from stock behaviour.
