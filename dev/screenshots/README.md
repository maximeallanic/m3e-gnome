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
dev/screenshots/make-video.sh [--work DIR] [--out DIR]    # 10-15 minutes; --from-raw DIR re-cuts an earlier recording
dev/screenshots/smoothness.py VIDEO --exact --gate         # the smoothness numbers below (VIDEO: lossless retimed frames)
```

**Recording.** The scenes of `video.py` (scenarios `video-dark`, `video-light`) are played in the nested Shell through the
same D-Bus API as the screenshots (virtual pointer and keyboard of the nested Shell, `Rect` to aim at real actors, `Glide`
for a smooth pointer travel clocked by the Shell). The screen is recorded by `org.gnome.Shell.Screencast` of the NESTED
Shell with its own DMABuf pipeline (cursor drawn, the orange recording indicator hidden).

**Why slow motion.** Recorded in real time, the Shell delivered 25-40 uneven frames per second (stalls of 60-400 ms,
mostly the first display of the app grid, menus and banners, and the capture itself on a loaded machine): not smooth.
So the capture is decoupled from the animation speed:

1. *Rehearsal*: every scene is played once, unrecorded, at normal speed, so the first-use costs (icons, shaders, actors)
   are paid before the recording starts.
2. *Slow-down*: the nested Shell's "Slow down animations" (`St.Settings.slow_down_factor`) is set to 4 (8 for the overview
   and app grid, the heaviest scene). The m3e springs (`shared/m3e/track.js`) and the stock transitions honour it; measured
   on the overview: 535 ms to show at factor 1, 2106 ms at factor 4 (x3.94), hide 585 ms and 2294 ms (x3.92). Every wait,
   key hold and pointer glide of the scenes is multiplied by the same factor (`wait()` in `video.py`).
3. *Retiming*: `mkvideo.py` cuts each scene by timestamp, divides the timestamps by its factor (`setpts=PTS/N`) and picks,
   for each 60 fps output instant, the nearest captured frame (`fps=60:round=near`: no blending, no interpolation). With
   about 35 captured frames per second of slowed time, an animation is sampled 140-280 times per second of real time, so
   frames are only dropped, never repeated. Every spring plays at its real duration.
4. *Gate*: `make-video.sh` measures the retimed lossless frames (`smoothness.py --exact --gate`) and records again (up to
   3 attempts) when a stretch of motion has a gap over 40 ms or over 20 % identical frames. The wait for an application to
   start (the only time nothing moves) is left out of the video, and the end of each scene is trimmed (at most 0.4 s) to
   make the total exactly 15.0 s. Scenes are joined with plain cuts, captions are DejaVu Sans Bold.

**Limits of the method.** What the Shell does not scale cannot be shown at true speed: GTK client animations (the Text
Editor's content, Settings), the 150 ms delay before the Alt+Tab popup, notification banner dwell time (4 s of real time is
0.5 s of video at factor 8; the banner scene only needs its arrival). The scenes avoid depending on them. Do Not Disturb is
pressed in the Quick Settings scene and `show-banners` reset afterwards (banners would otherwise be suppressed); the
accessibility indicator is shown only for the switch scene. The light palette is a second session (a live switch would
need the Shell and GTK stylesheets swapped at run time, which the theme does not do). A scenario must end within 2 minutes
(the wait of `nested.sh`), which bounds the factor.

**Measured on the shipped video** (60 fps, 900 frames, 1920x1080; the real clock in the top bar is the host's):
in the lossless retimed frames, 0 exactly duplicated frames and a widest gap between distinct pictures of 17 ms inside the
motion stretches (stretches = runs of frames whose mean luma difference exceeds 0.1 on the 0-255 scale: 14 stretches, 217
frames); same numbers on the H.264 file (threshold 0.2): 0 duplicates, 16.7 ms, no gap over 40 ms. Tails where an
animation settles by less than a pixel per frame are, correctly, identical frames and are outside the stretches. The WebP
(800 px, 50 fps) has 496 frames, delays from 20 ms (a still moment is one longer frame, up to 280 ms), none under 20 ms.
The energy profile of the overview opening (mean luma difference per frame): 2.6, 11.2, 15.2, 17.1, 16.3, 13.6, 11.5, 8.8,
6.8, 6.8, 4.4, 4.5, 2.9, 1.4 (rises, peaks, then settles monotonically over 14 frames = 0.23 s).
Same privacy rules as above: look at frames of every scene before publishing.
