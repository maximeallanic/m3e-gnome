"""Helpers of the GTK bench scenarios: the D-Bus API of the bench extension (virtual pointer and keyboard of the
NESTED Shell, window geometry, screenshots) and the start/stop of the applications under test.

Only runs inside the private session bus of the nested Shell (the extension is the owner of the D-Bus name).
Applications are stopped by process group of the PID started here, never by name: a `pkill ptyxis` would kill the
terminal of the real session.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from gi.repository import Gio, GLib

NAME = os.environ.get("M3E_BENCH_GTK_NAME", "io.github.maximeallanic.M3eBenchGtk")
PATH = os.environ.get("M3E_BENCH_GTK_PATH", "/io/github/maximeallanic/M3eBenchGtk")
BUS = Gio.bus_get_sync(Gio.BusType.SESSION)
CTRL, SHIFT, RETURN, PAGE_DOWN = 0xffe3, 0xffe1, 0xff0d, 0xff56

# Environment of the applications: nested display (WAYLAND_DISPLAY comes from the extension), no portal (libadwaita
# reads color-scheme from the private dconf), no accessibility bus, no gvfs daemons.
APP_ENV = {"GDK_BACKEND": "wayland", "ADW_DISABLE_PORTAL": "1", "GTK_USE_PORTAL": "0", "NO_AT_BRIDGE": "1",
           "GTK_A11Y": "none", "GIO_USE_VFS": "local", "GIO_USE_VOLUME_MONITOR": "unix"}


def call(method, signature=None, *args, timeout=10000):
    params = GLib.Variant(signature, args) if signature else None
    reply = BUS.call_sync(NAME, PATH, NAME, method, params, None, Gio.DBusCallFlags.NONE, timeout, None)
    return reply.unpack() if reply else None


def pause(seconds):
    time.sleep(seconds)


def pointer(x, y):
    call("Pointer", "(dd)", float(x), float(y))


def click(button, pressed):
    call("Click", "(ub)", button, pressed)


def wheel(dy, times=1, dx=0.0):
    for _ in range(times):
        call("Wheel", "(dd)", float(dx), float(dy))
        pause(0.03)


def keys(*keyvals):
    for k in keyvals:
        call("Key", "(ub)", k, True)
    for k in reversed(keyvals):
        call("Key", "(ub)", k, False)
    pause(0.05)


def type_text(text):
    for c in text:
        keys(RETURN if c == "\n" else ord(c))


def maximize(wm_class):
    call("Maximize", "(s)", wm_class)


def windows():
    return json.loads(call("Windows")[0])


def capture(out, name):
    try:
        call("Capture", "(s)", str(Path(out) / f"{name}.png"), timeout=20000)
    except GLib.Error as e:
        print(f"capture {name}: {e.message}", file=sys.stderr)


def wait_window(before, timeout=25):
    """First new window after `before` (a list of windows()), once it had 1.5 s to settle; None on timeout."""
    ids = {w["id"] for w in before}
    end = time.time() + timeout
    while time.time() < end:
        if [w for w in windows() if w["id"] not in ids]:
            pause(1.5)
            return [w for w in windows() if w["id"] not in ids][0]
        pause(0.3)
    return None


def sweep(w, step=48, delay=0.02):
    """Pointer moved in a serpentine over the whole window: every hovered element goes through :hover."""
    y, direction = w["y"] + 8, 1
    while y < w["y"] + w["h"]:
        xs = range(w["x"] + 8, w["x"] + w["w"], step)
        for x in (xs if direction > 0 else reversed(list(xs))):
            pointer(x, y)
            pause(delay)
        y += step
        direction = -direction


def start(out, name, argv, env=None):
    log = open(Path(out) / f"journal-{name}.log", "w", encoding="utf-8")
    full_env = dict(os.environ, **APP_ENV, **(env or {}))
    proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=full_env, start_new_session=True)
    return proc, log


def stop(proc, log):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    log.close()
