"""State shared by the test shims (gsettings, dconf, gnome-extensions, systemctl, ...).

Everything lives under $M3E_FAKE_DIR, outside the temporary HOME: dconf.json maps dconf paths to GVariant text,
schemas.txt lists the installed schemas, services.json holds the user services, calls.log records every call.
The shims never reach a real session bus or the real user's settings."""
import json
import os
import sys
from pathlib import Path

FAKE = Path(os.environ["M3E_FAKE_DIR"])

# Values GSettings reports for keys that are not set in dconf.
DEFAULTS = {
    "/org/gnome/desktop/interface/gtk-theme": "'Adwaita'",
    "/org/gnome/desktop/interface/icon-theme": "'Adwaita'",
    "/org/gnome/desktop/interface/cursor-theme": "'Adwaita'",
    "/org/gnome/desktop/interface/cursor-size": "24",
    "/org/gnome/desktop/interface/color-scheme": "'default'",
    "/org/gnome/desktop/interface/accent-color": "'blue'",
    "/org/gnome/desktop/interface/font-name": "'Adwaita Sans 11'",
    "/org/gnome/desktop/wm/preferences/titlebar-font": "'Adwaita Sans Bold 11'",
    "/org/gnome/desktop/wm/preferences/button-layout": "'appmenu:close'",
    "/org/gnome/desktop/sound/theme-name": "'freedesktop'",
    "/org/gnome/desktop/sound/event-sounds": "true",
    "/org/gnome/shell/enabled-extensions": "@as []",
    "/org/gnome/shell/extensions/user-theme/name": "''",
    "/org/gnome/shell/extensions/dash-to-dock/apply-custom-theme": "false",
    "/org/gnome/desktop/background/picture-uri": "''",
    "/org/gnome/desktop/background/picture-uri-dark": "''",
    "/org/gnome/Ptyxis/default-profile-uuid": "'0123abcd'",
}


def log(line):
    with (FAKE / "calls.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load():
    p = FAKE / "dconf.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save(store):
    (FAKE / "dconf.json").write_text(json.dumps(store, indent=1, sort_keys=True))


def path_of(schema, key):
    if ":" in schema:
        return schema.split(":", 1)[1] + key
    return "/" + schema.replace(".", "/") + "/" + key


def schemas():
    p = FAKE / "schemas.txt"
    return p.read_text().split() if p.exists() else []


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)
