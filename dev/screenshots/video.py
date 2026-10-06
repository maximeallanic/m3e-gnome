#!/usr/bin/env python3
"""Scenes of the animation video, played INSIDE the private session bus of the nested Shell (see shots.py: scenarios
`video-dark` and `video-light`).

The scene is recorded in real time by org.gnome.Shell.Screencast of the nested Shell (a PipeWire stream of the virtual
monitor, encoded by GStreamer; the file is variable-frame-rate: a frame per change of the screen). Waits that carry no
animation (the start of an application) are not cut here but listed in marks.json: make-video.sh keeps only the
[start, end] intervals of the scenes, so the recording itself is never speeded up or slowed down.

Output (in the scenario output directory): raw-<mode>.<ext> (the recording) and marks-<mode>.json
{"file": ..., "scenes": [{"name", "start", "end"}]} with times in seconds on the recording clock.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from gi.repository import Gio, GLib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m3e-bench-gtk"))
import driver as d  # noqa: E402

SCREEN = (1920, 1080)
ALT_L, TAB, ESC, F4 = 0xffe9, 0xff09, 0xff1b, 0xffc1
FRAMERATE = 60
# Recording pipeline (appended to the source by the Shell). The default one (openh264, 2 queues of a few buffers) drops
# frames while the Shell is busy animating; here the buffers are unbounded so that no frame is dropped between the
# stream and the encoder, and the encoder is a fast, near-lossless x264 (the final encode is done by mkvideo.py).
UNBOUNDED = "queue max-size-buffers=0 max-size-time=0 max-size-bytes=0"
PIPELINE = (f"{UNBOUNDED} ! videoconvert n-threads=4 ! video/x-raw,format=I420 ! "
            f"{UNBOUNDED} ! x264enc speed-preset=ultrafast pass=qual quantizer=14 threads=6 ! h264parse ! matroskamux")
SCREENCAST = ("org.gnome.Shell.Screencast", "/org/gnome/Shell/Screencast", "org.gnome.Shell.Screencast")


def action(name, arg=""):
    d.call("Action", "(ss)", name, arg)


def rect(selector):
    r = json.loads(d.call("Rect", "(s)", selector)[0])
    if any(v is None for v in r.values()):
        raise RuntimeError(f"{selector}: no geometry yet ({r})")
    return r


def centre(r):
    return r["x"] + r["w"] / 2, r["y"] + r["h"] / 2


def glide(x, y, seconds=0.35):
    """Pointer moved smoothly by the Shell itself (the cursor is drawn: the viewer follows it)."""
    d.call("Glide", "(ddd)", float(x), float(y), float(seconds))
    d.pause(seconds)


def press(hold=0.22):
    d.click(1, True)
    d.pause(hold)
    d.click(1, False)


def click_on(selector, seconds=0.35, hold=0.15):
    x, y = centre(rect(selector))
    glide(x, y, seconds)
    d.pause(0.1)
    press(hold)


def tap(*keyvals):
    d.keys(*keyvals)


class Recorder:
    """Screencast of the nested Shell, and the scene marks on its clock."""

    def __init__(self, out, mode):
        self.out, self.mode, self.scenes, self.open, self.t0 = Path(out), mode, [], None, None

    def _call(self, method, signature=None, *args):
        params = GLib.Variant(signature, args) if signature else None
        return d.BUS.call_sync(*SCREENCAST[:2], SCREENCAST[2], method, params, None, Gio.DBusCallFlags.NONE, 10000, None)

    def start(self):
        options = {"framerate": GLib.Variant("i", FRAMERATE), "draw-cursor": GLib.Variant("b", True),
                   "pipeline": GLib.Variant("s", PIPELINE)}
        ok, self.file = self._call("Screencast", "(sa{sv})", str(self.out / f"raw-{self.mode}"), options).unpack()
        self.t0 = time.monotonic()
        if not ok:
            raise RuntimeError("Screencast refused")

    def begin(self, name, shift=0.0):
        self.open = (name, time.monotonic() - self.t0 + shift)

    def end(self):
        name, start = self.open
        self.scenes.append({"name": name, "start": round(start, 3), "end": round(time.monotonic() - self.t0, 3)})
        self.open = None

    def stop(self):
        self._call("StopScreencast")
        raw = Path(self.file)
        if raw.suffix == ".undefined":              # a custom pipeline has no file extension: it is Matroska
            raw = raw.rename(raw.with_suffix(".mkv"))
        marks = {"file": raw.name, "framerate": FRAMERATE, "scenes": self.scenes}
        (self.out / f"marks-{self.mode}.json").write_text(json.dumps(marks, indent=1), encoding="utf-8")


def park():
    d.pointer(SCREEN[0] - 4, SCREEN[1] - 4)


def scene_overview(rec):
    """Overview, app grid, launch of an application from its icon (window open), Ctrl+W (window close)."""
    rec.begin("overview")
    action("overview")
    d.pause(0.8)
    action("appgrid")
    d.pause(0.8)
    known = {w["id"] for w in d.windows()}
    x, y = centre(rect("app:org.gnome.TextEditor.desktop"))
    glide(x, y, 0.3)
    d.pause(0.05)
    press(0.1)
    d.pause(0.5)                    # the overview closes while the application starts
    rec.end()
    # Nothing moves until the window appears: that wait is left out of the video (the scene ends above and the next
    # one starts just before the window is mapped).
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not [w for w in d.windows() if w["id"] not in known]:
        d.pause(0.04)
    if time.monotonic() >= deadline:
        raise RuntimeError("the text editor did not open")
    rec.begin("window", -0.05)
    d.pause(0.8)
    d.call("Key", "(ub)", ALT_L, True)
    tap(F4)
    d.call("Key", "(ub)", ALT_L, False)
    d.pause(0.6)
    rec.end()
    park()


def scene_quick_settings(rec):
    rec.begin("quick-settings")
    click_on("panel:quickSettings", 0.3)
    d.pause(0.5)
    click_on("tile:Do Not Disturb", 0.3, 0.25)
    d.pause(0.35)
    tap(ESC)
    d.pause(0.2)
    rec.end()
    park()


def banners_back():
    """The Do Not Disturb tile was pressed: show banners again (private dconf of the nested session) for what follows."""
    Gio.Settings.new("org.gnome.desktop.notifications").reset("show-banners")
    Gio.Settings.sync()
    d.pause(0.3)


def a11y(on):
    s = Gio.Settings.new("org.gnome.desktop.a11y")
    s.set_boolean("always-show-universal-access-status", on)
    Gio.Settings.sync()


def scene_switch(rec):
    """Popup menu with M3E switches (the accessibility menu: Visual Alerts only changes how the bell is shown)."""
    rec.begin("switch")
    click_on("panel:a11y", 0.3)
    d.pause(0.45)
    click_on("switch:5", 0.25, 0.15)
    d.pause(0.35)
    tap(ESC)
    d.pause(0.2)
    rec.end()
    park()


NOTIFICATIONS = [("Messages", "internet-mail", "Alex Rivera", "Are we still on for lunch tomorrow?"),
                 ("Calendar", "x-office-calendar", "Design review in 10 minutes", "Meeting room 2, with Sam and Priya.")]


def notify(i):
    app, icon, title, body = NOTIFICATIONS[i]
    subprocess.run(["notify-send", "-a", app, "-i", icon, title, body], check=True)


def scene_notifications(rec):
    rec.begin("notifications")
    notify(0)
    d.pause(0.7)
    notify(1)
    d.pause(0.25)
    click_on("panel:dateMenu", 0.3)
    d.pause(0.9)
    tap(ESC)
    d.pause(0.2)
    rec.end()
    park()


def scene_alt_tab(rec, settings):
    d.call("Activate", "(u)", settings["id"])
    d.pause(0.4)
    rec.begin("alt-tab")
    d.call("Key", "(ub)", ALT_L, True)
    d.pause(0.1)
    tap(TAB)
    d.pause(0.5)
    tap(TAB)
    d.pause(0.4)
    d.call("Key", "(ub)", ALT_L, False)
    d.pause(0.5)
    rec.end()


def scene_light(rec):
    scene_quick_settings(rec)


def run(mode, apps_class, place):
    """Apps and Shell state prepared outside the recording, then the scenes of `mode` (dark: all, light: a short one)."""
    out = Path(os.environ["M3E_BENCH_OUT"])
    if not os.environ.get("M3E_BENCH_TMP") or not os.environ.get("XDG_CONFIG_HOME", "").startswith(os.environ["M3E_BENCH_TMP"]):
        raise RuntimeError("refusing to change settings: the session is not the private nested one")
    apps = apps_class()
    rec = Recorder(out, mode)
    # Airplane mode and the Bluetooth tile come from the settings daemon's rfkill service (absent in a nested session).
    rfkill = subprocess.Popen([os.environ.get("M3E_SHOTS_PYTHON", sys.executable), "-m", "dbusmock", "--template",
                               "gsd_rfkill"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        d.pause(1.0)
        files, terminal, settings = apps.files(), apps.terminal(), apps.settings()
        place(settings, 70, 100, 980, 470)
        place(files, 900, 150, 960, 600)
        place(terminal, 420, 540, 1000, 420)
        action("clear-notifications")
        park()
        d.pause(1.5)
        action("hide-recording-indicator")
        rec.start()
        d.pause(0.3)
        if mode == "light":
            scene_light(rec)
        else:
            scene_overview(rec)
            scene_quick_settings(rec)
            banners_back()
            a11y(True)
            d.pause(0.5)
            scene_switch(rec)
            a11y(False)
            scene_notifications(rec)
            scene_alt_tab(rec, settings)
    finally:
        try:
            rec.stop()
        finally:
            a11y(False)
            apps.close()
            rfkill.terminate()
