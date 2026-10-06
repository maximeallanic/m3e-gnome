#!/usr/bin/env python3
"""Scenarios of the screenshot session, started by the m3e-shots extension INSIDE the private session bus of the
nested Shell.

Usage: shots.py <out_dir> <scenario>        scenario: all | apps | shell | palette
  apps   one real GTK 4 / libadwaita application at a time, centred on the wallpaper (settings, files, terminal)
  shell  the three applications open, then the Shell surfaces: desktop, overview, app grid, Alt+Tab, quick settings
         (and the Wi-Fi submenu), notifications and calendar, modal dialog, volume OSD
  palette  files + settings windows and the quick settings, one capture (used for the wallpaper montage)
Output: <out_dir>/<name>.png (whole 1920x1080 screen, scale 1). Applications are stopped by process group of the PID
started here, never by name.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m3e-bench-gtk"))
import driver as d  # noqa: E402

OUT = Path(sys.argv[1])
SCENARIO = sys.argv[2]
HOME = Path(os.environ["HOME"])
SCREEN = (1920, 1080)
ALT_L, TAB = 0xffe9, 0xff09
TERMINAL_SCRIPT = r"""
cd ~
export LS_COLORS='di=34:ln=36:ex=32:*.zip=31:*.deb=31:*.png=35:*.mp4=35:*.webm=35:*.flac=36:*.ogg=36:*.mp3=36'
export PS1='\[\e[32m\]demo@m3e\[\e[0m\]:\[\e[34m\]\w\[\e[0m\]\$ '
p() { printf '\033[32mdemo@m3e\033[0m:\033[34m~\033[0m$ %s\n' "$1"; }
p 'ls --color=always -NF Documents Music Pictures Projects'
ls --color=always -NF Documents Music Pictures Projects
echo
p 'ls --color=always -NF Downloads Videos'
ls --color=always -NF Downloads Videos
echo
p './palette.sh'
for base in 40 100; do
  for c in 0 1 2 3 4 5 6 7; do printf '\033[%dm      \033[0m' $((base + c)); done; echo
done
echo
exec bash --norc --noprofile
"""
# (application name, icon, summary, body). Icons with their own colours: the white ones of the dark icon theme vanish on light cards. The names deliberately match no desktop entry: the Shell of a nested session
# drops the notifications of applications it can resolve to an installed launcher (observed with org.gnome.Nautilus and
# org.gnome.Software), while plain names are listed and shown as banners.
NOTIFICATIONS = [
    ("Messages", "internet-mail", "Alex Rivera", "Are we still on for lunch tomorrow? I booked the corner table."),
    ("Calendar", "x-office-calendar", "Design review in 10 minutes", "Meeting room 2, with Sam and Priya."),
    ("Software", "org.gnome.Software", "Updates are ready", "6 applications can be updated."),
    ("Files", "folder-download", "Download complete", "invoice-0412.pdf was saved in Downloads."),
]


def action(name, arg=""):
    d.call("Action", "(ss)", name, arg)


def place(window, x, y, w, h):
    d.call("Place", "(uiiii)", window["id"], x, y, w, h)


def centred(window, w=1280, h=800):
    place(window, (SCREEN[0] - w) // 2, (SCREEN[1] - h) // 2 + 20, w, h)


def shot(name, delay=1.0):
    d.pause(delay)
    d.capture(OUT, name)
    print(f"captured {name}", flush=True)


class Apps:
    """Applications started here; stopped by PID in close()."""

    def __init__(self):
        self.running = []

    def open(self, name, argv, env=None):
        before = d.windows()
        proc, log = d.start(OUT, name, argv, env)
        self.running.append((proc, log))
        window = d.wait_window(before, timeout=40)
        if not window:
            raise RuntimeError(f"{name}: no window")
        return window

    def terminal(self):
        script = Path(os.environ["XDG_CACHE_HOME"]) / "demo-terminal.sh"
        script.write_text(TERMINAL_SCRIPT, encoding="utf-8")
        # No systemd-run on PATH: Ptyxis then starts the shell itself (no transient scope in a user manager).
        bin_dir = Path(os.environ["XDG_CACHE_HOME"]) / "bin"
        bin_dir.mkdir(exist_ok=True)
        for b in Path("/usr/bin").iterdir():
            if b.name != "systemd-run" and not (bin_dir / b.name).exists():
                (bin_dir / b.name).symlink_to(b)
        return self.open("terminal", ["ptyxis", "--standalone", "-x", f"bash {script}"],
                         {"PATH": str(bin_dir), "HISTFILE": "/dev/null"})

    def files(self):
        return self.open("files", ["nautilus", "--new-window", str(HOME)])

    def settings(self):
        return self.open("settings", ["gnome-control-center", "background"])

    def close(self):
        for proc, log in self.running:
            d.stop(proc, log)
        self.running = []
        d.pause(1.0)


def scenario_apps():
    # Settings is cut above its "Background" section (GNOME's own wallpaper thumbnails are not ours to publish).
    for name, opener, size in (("settings", Apps.settings, (1280, 470)), ("files", Apps.files, (1280, 800)),
                               ("terminal", Apps.terminal, (1100, 700))):
        apps = Apps()
        try:
            window = opener(apps)
            centred(window, *size)
            action("clear-notifications")
            if name == "files":
                select_first_item(window)
            d.pointer(SCREEN[0] // 2, SCREEN[1] - 10)
            shot(f"app-{name}", 1.5)
        finally:
            apps.close()


def select_first_item(window):
    """Click the first icon of the Files grid (selection highlight) and leave the pointer elsewhere."""
    x, y = window["x"] + 368, window["y"] + 125
    d.pointer(x, y)
    d.pause(0.3)
    d.click(1, True)
    d.click(1, False)
    d.pause(0.5)


def notify_all():
    for app, icon, title, body in NOTIFICATIONS:
        subprocess.run(["notify-send", "-a", app, "-i", icon, title, body], check=True)
        d.pause(0.15)


def scenario_shell():
    apps = Apps()
    # Airplane mode and the Bluetooth tile come from the settings daemon's rfkill service (absent in a nested session).
    rfkill = subprocess.Popen([os.environ.get("M3E_SHOTS_PYTHON", sys.executable), "-m", "dbusmock", "--template", "gsd_rfkill"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        files, terminal, settings = apps.files(), apps.terminal(), apps.settings()
        place(settings, 70, 100, 980, 470)
        place(files, 900, 150, 960, 600)
        place(terminal, 420, 540, 1000, 420)
        action("clear-notifications")
        d.pointer(SCREEN[0] - 4, SCREEN[1] - 4)
        shot("desktop", 2.0)
        action("overview")
        shot("overview", 2.0)
        action("appgrid")
        shot("app-grid", 2.0)
        action("close")
        d.pause(1.0)
        d.call("Activate", "(u)", settings["id"])
        d.pause(0.5)
        d.call("Key", "(ub)", ALT_L, True)
        d.keys(TAB)
        shot("alt-tab", 1.0)
        d.call("Key", "(ub)", ALT_L, False)
        d.pause(0.8)
        action("quick-settings")
        shot("quick-settings", 1.2)
        action("close")
        d.pause(0.5)
        action("quick-settings", "Wi-Fi")
        shot("quick-settings-wifi", 1.2)
        action("close")
        d.pause(0.5)
        action("clear-notifications")
        notify_all()
        shot("notification-banner", 0.8)
        d.pause(5.0)
        action("calendar")
        shot("notifications", 1.2)
        action("close")
        action("clear-notifications")
        d.pause(0.5)
        action("dialog")
        shot("dialog", 1.0)
        action("close")
        d.pause(1.2)
        action("osd-volume")
        shot("osd", 0.4)
    finally:
        apps.close()
        rfkill.terminate()


def scenario_palette():
    """One capture per wallpaper for the palette montage: two windows and the quick settings open."""
    apps = Apps()
    try:
        files, settings = apps.files(), apps.settings()
        place(files, 140, 150, 1100, 700)
        place(settings, 420, 260, 1100, 470)
        action("clear-notifications")
        d.pointer(SCREEN[0] - 4, SCREEN[1] - 4)
        action("quick-settings")
        shot("palette", 1.5)
    finally:
        apps.close()


def scenario_notify():
    """Notifications alone (quick iteration on the notification list)."""
    action("clear-notifications")
    notify_all()
    shot("notify-banner", 0.8)
    d.pause(5.0)
    action("calendar")
    shot("notify-list", 1.2)


SCENARIOS = {"notify": scenario_notify, "apps": scenario_apps, "shell": scenario_shell, "palette": scenario_palette}


def main():
    names = ["apps", "shell"] if SCENARIO == "all" else [SCENARIO]
    code = 0
    for name in names:
        t0 = time.time()
        try:
            SCENARIOS[name]()
            print(f"scenario {name}: played in {time.time() - t0:.0f} s", flush=True)
        except Exception as e:  # noqa: BLE001 - a failing scenario does not stop the next one
            print(f"scenario {name}: error {e!r}", file=sys.stderr)
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
