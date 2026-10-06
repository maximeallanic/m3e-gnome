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
| `make-video.sh`, `video.py`, `mkvideo.py` | The animation video (below): recording orchestrator, the scenes played in the nested Shell, the cutting and encoding. |
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

## Animation video (`screenshots/animations.mp4`)

```sh
dev/screenshots/make-video.sh [--work DIR] [--out DIR]    # about 5 minutes; --from-raw DIR re-cuts an earlier run
```

How it records: the scenes of `video.py` (scenarios `video-dark`, `video-light`) are played in the nested Shell through the
same D-Bus API as the screenshots (virtual pointer and keyboard of the nested Shell, `Rect` to aim at real actors, `Glide`
for a smooth pointer travel clocked by the Shell). The screen is recorded in real time by `org.gnome.Shell.Screencast` of
the NESTED Shell (PipeWire stream of its virtual monitor, x264 near-lossless through a pipeline with unbounded queues,
cursor drawn, the orange recording indicator hidden). Nothing is speeded up: `marks-<mode>.json` lists the interval of every
scene on the recording clock and `mkvideo.py` keeps only those intervals (the wait for an application to start is the
only thing cut), joins them with plain cuts, adds the captions (DejaVu Sans Bold) and encodes H.264 yuv420p, faststart,
1920x1080, 30 fps, 15.0 s; then the WebP (800 px, 30 fps, looping) and the poster frame. The recording is variable-frame-rate
(one frame per screen change); `fps` makes it constant by timestamp, so every spring keeps its real duration.
The last 1.2 s of trimming is taken from scene tails (`fit()`); if the scenes ever run longer, `mkvideo.py` says so.

Frame rate: the Shell produces about 35-40 distinct frames per second while animating on the reference machine (1080p,
integrated GPU, loaded host), hence the 30 fps output; on a quiet machine `--fps 60` is meaningful. Light palette: a second
session (a live dark/light switch would need the Shell and GTK stylesheets to be swapped at run time, which the theme does
not do), shown for the last scene. The Do Not Disturb tile is pressed in the Quick Settings scene and its setting reset
afterwards (banners would otherwise be suppressed); the accessibility indicator is shown only for the switch scene.
Same privacy rules as above: look at frames of every scene before publishing.
