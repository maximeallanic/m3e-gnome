#!/usr/bin/env python3
"""Scenarios of the GTK bench, started by the bench extension INSIDE the private session bus of the nested Shell.

Usage: scenario.py <out_dir> <scenarios separated by commas> <bench dir>
Each scenario starts an application (stderr journal in <out>/journal-<scenario>.log), drives it through the bench
extension (virtual pointer and keyboard of the nested Shell), takes screenshots, then stops it by PID.
  client4    : client-gtk4.py (AdwTabBar tabs opened/closed, scrollbars, sliders, switches, buttons; frame by frame
               trace of the transitions)
  client3    : client-gtk3.py (same families in GTK 3)
  ptyxis     : standalone Ptyxis, 4 tabs opened then closed from the keyboard, tab hover, terminal scrolling and
               scrollbar hover
  files      : Files on /usr/share/applications: pointer sweep, scrolling (view and sidebar)
  calculator : Calculator: sweep, scrolling
  settings   : Settings, Mouse panel (sliders): sweep and scrolling, no click
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import driver as d

OUT, SCENARIOS, HERE = Path(sys.argv[1]), sys.argv[2].split(","), Path(sys.argv[3])
MODE = os.environ.get("M3E_BENCH_MODE", "dark")


def run_client(name, script, env=None):
    proc, log = d.start(OUT, name, [sys.executable, str(HERE / script), str(OUT)], env)
    timed_out = False
    try:
        proc.wait(240)
    except subprocess.TimeoutExpired:
        timed_out = True
    d.stop(proc, log)
    if timed_out:
        raise RuntimeError(f"{name}: client still running after 240 s (stopped)")


def s_client4():
    run_client("client4", "client-gtk4.py")


def s_client3():
    run_client("client3", "client-gtk3.py", {"GTK_THEME": "Material-Gnome:dark" if MODE == "dark" else "Material-Gnome"})


def terminal_bin_dir():
    """PATH without systemd-run: Ptyxis then starts the shell directly (no scope in a systemd manager)."""
    cache = Path(os.environ["XDG_CACHE_HOME"])
    path = cache / "bin"
    path.mkdir(exist_ok=True)
    for b in Path("/usr/bin").iterdir():
        if b.name != "systemd-run" and not (path / b.name).exists():
            (path / b.name).symlink_to(b)
    return cache, path


def s_ptyxis():
    before = d.windows()
    cache, bin_dir = terminal_bin_dir()
    # bash without init files nor history; the working directory is the private cache.
    proc, log = d.start(OUT, "ptyxis", ["ptyxis", "--standalone", "--maximize", "-d", str(cache)],
                        {"PATH": str(bin_dir), "HISTFILE": "/dev/null", "PS1": "$ "})
    try:
        w = d.wait_window(before)
        if not w:
            print("ptyxis: no window", file=sys.stderr)
            return
        d.maximize(w["wm_class"])
        d.pause(1.5)
        d.capture(OUT, "ptyxis-0-maximized")
        print("ptyxis window:", w, file=sys.stderr)
        w = [x for x in d.windows() if x["id"] == w["id"]][0]
        cx, cy = w["x"] + w["w"] // 2, w["y"] + w["h"] // 2
        d.pointer(cx, cy)
        d.type_text("seq")
        d.pause(0.5)
        d.capture(OUT, "ptyxis-0b-typed")
        d.type_text(" 1 600\n")
        d.pause(1)
        d.capture(OUT, "ptyxis-1-tab")
        for i in range(3):                       # 3 more tabs: AdwTabBox opening animation
            d.keys(d.CTRL, d.SHIFT, ord("T"))
            d.pause(0.8)
            d.type_text(f"seq 1 {300 * (i + 2)}\n")
            d.pause(0.4)
        d.pause(1)
        d.capture(OUT, "ptyxis-4-tabs")
        tab_y = w["y"] + 40 + 20                 # 40 px title bar, 34 px tabs under 6 px
        for k in range(4):                        # hover each tab then its close button
            x = w["x"] + 8 + (w["w"] - 16) * (k + 0.5) / 4
            d.pointer(x, tab_y)
            d.pause(0.35)
            d.pointer(x + (w["w"] - 16) / 8 - 30, tab_y)
            d.pause(0.35)
        d.capture(OUT, "ptyxis-tab-hover")
        d.keys(d.CTRL, d.PAGE_DOWN)
        d.pause(0.5)
        d.pointer(cx, cy)
        d.wheel(-1, 40)                          # scroll back: the overlay scrollbar appears
        d.pause(0.2)
        for x in range(w["x"] + w["w"] - 60, w["x"] + w["w"], 4):   # towards the bar: indicator -> hovered bar
            d.pointer(x, cy)
            d.pause(0.03)
        d.pause(0.6)
        d.capture(OUT, "ptyxis-scrollbar-hover")
        d.click(1, True)
        d.pause(0.4)
        d.click(1, False)
        d.pause(0.3)
        d.pointer(cx, cy)                        # leave the bar: back to the indicator
        d.pause(1.5)
        d.wheel(1, 40)
        d.pause(1.5)
        for _ in range(3):                       # close the tabs: closing animation
            d.keys(d.CTRL, d.SHIFT, ord("W"))
            d.pause(0.9)
        d.capture(OUT, "ptyxis-closed")
        d.pause(1)
    finally:
        d.stop(proc, log)


def s_app(name, argv, maximize=False, wheels=((0.5, 0.5),)):
    before = d.windows()
    proc, log = d.start(OUT, name, argv)
    try:
        w = d.wait_window(before)
        if not w:
            print(f"{name}: no window", file=sys.stderr)
            return
        if maximize:
            d.maximize(w["wm_class"])
            d.pause(1.5)
            w = [x for x in d.windows() if x["id"] == w["id"]][0]
        d.capture(OUT, f"{name}-open")
        d.sweep(w)
        for rx, ry in wheels:
            x0, y0 = int(w["x"] + w["w"] * rx), w["y"] + w["h"] * ry
            d.pointer(x0, y0)
            d.pause(0.2)
            d.wheel(1, 30)
            d.pause(0.5)
            for x in range(x0, x0 + 400, 6):
                d.pointer(x, y0)
                d.pause(0.02)
            d.pause(1.2)
            d.wheel(-1, 30)
            d.pause(1.2)
        d.capture(OUT, f"{name}-end")
    finally:
        d.stop(proc, log)


KNOWN = {
    "client4": s_client4,
    "client3": s_client3,
    "ptyxis": s_ptyxis,
    "files": lambda: s_app("files", ["nautilus", "--new-window", "/usr/share/applications"],
                           wheels=((0.6, 0.5), (0.1, 0.5))),
    "calculator": lambda: s_app("calculator", ["gnome-calculator"]),
    "settings": lambda: s_app("settings", ["gnome-control-center", "mouse"], wheels=((0.15, 0.5), (0.6, 0.5))),
}


def main():
    code = 0
    for s in SCENARIOS:
        if s not in KNOWN:
            print(f"unknown scenario: {s}", file=sys.stderr)
            code = 2
            continue
        t0 = time.time()
        try:
            KNOWN[s]()
            print(f"scenario {s}: played in {time.time() - t0:.0f} s")
        except Exception as e:  # noqa: BLE001 - a failing scenario does not stop the next ones
            print(f"scenario {s}: error {e!r}", file=sys.stderr)
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
