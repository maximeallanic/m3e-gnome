"""Fake home directory, applications and fonts configuration of the screenshot session (everything invented).

The nested Shell and its applications run with HOME pointing at <out>/home/demo, so that no real file, user name or
path can appear in a capture (Files sidebar and path bar, application menus, recent files).
"""
from pathlib import Path

from PIL import Image

import wallpapers

# Desktop entries kept visible in the application grid (GNOME core applications installed from the distribution).
KEEP_APPS = {
    "org.gnome.Calculator", "org.gnome.DiskUtility", "org.gnome.Extensions", "org.gnome.FileRoller",
    "org.gnome.font-viewer", "org.gnome.Loupe", "org.gnome.Nautilus", "org.gnome.Papers", "org.gnome.Ptyxis",
    "org.gnome.Settings", "org.gnome.Showtime", "org.gnome.Software", "org.gnome.SystemMonitor",
    "org.gnome.TextEditor", "org.gnome.tweaks", "org.gnome.Yelp",
}
# Launchers that only exist to fill the grid like a complete desktop: name, icon (from Papirus). They run `true`.
DEMO_LAUNCHERS = [("Calendar", "org.gnome.Calendar"), ("Clocks", "org.gnome.clocks"), ("Weather", "org.gnome.Weather"),
                  ("Maps", "org.gnome.Maps"), ("Contacts", "org.gnome.Contacts"), ("Music", "org.gnome.Music"),
                  ("Camera", "org.gnome.Snapshot"), ("Characters", "org.gnome.Characters"),
                  ("Logs", "org.gnome.Logs"), ("Mail", "org.gnome.Geary")]
FAVORITES = ["org.gnome.Nautilus.desktop", "org.gnome.Ptyxis.desktop", "org.gnome.Settings.desktop",
             "org.gnome.TextEditor.desktop", "org.gnome.Calculator.desktop"]

FOLDERS = {
    "Documents": ["Budget 2026.ods", "Meeting notes.md", "Trip itinerary.pdf", "Report draft.odt", "Contract.pdf"],
    "Downloads": ["installer.deb", "invoice-0412.pdf", "slides.odp", "archive.zip"],
    "Music": ["Morning Light.flac", "Slow River.ogg", "Night Drive.mp3"],
    "Videos": ["Holiday clip.mp4", "Screen recording.webm"],
    "Projects": ["website", "notes", "scripts"],
}
PHOTOS = ["dunes", "ocean", "dusk", "forest"]


def make_home(home, size=(480, 320)):
    """Create the demo home tree: folders with empty typed files, a few generated pictures, user-dirs.dirs."""
    for folder, files in FOLDERS.items():
        directory = home / folder
        directory.mkdir(parents=True, exist_ok=True)
        for name in files:
            if "." in name:
                (directory / name).write_text("demo\n", encoding="utf-8")
            else:
                (directory / name).mkdir(exist_ok=True)
    pictures = home / "Pictures"
    pictures.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(PHOTOS):
        wallpapers.scene(name, size).save(pictures / f"Photo {index + 1}.png")
    (home / "Desktop").mkdir(exist_ok=True)
    (home / "Public").mkdir(exist_ok=True)
    (home / "Templates").mkdir(exist_ok=True)


def user_dirs():
    """user-dirs.dirs content (without it the folders of the home would not be recognised as Documents, ...)."""
    names = {"DESKTOP": "Desktop", "DOWNLOAD": "Downloads", "TEMPLATES": "Templates", "PUBLICSHARE": "Public",
             "DOCUMENTS": "Documents", "MUSIC": "Music", "PICTURES": "Pictures", "VIDEOS": "Videos"}
    return "".join(f'XDG_{k}_DIR="$HOME/{v}"\n' for k, v in names.items())


def make_applications(target, system_dirs=("/usr/share/applications", "/usr/local/share/applications")):
    """Write into `target` a Hidden=true entry for every system launcher not in KEEP_APPS, and the demo launchers.
    Placed first in XDG_DATA_DIRS, so the application grid only shows the kept ones."""
    target.mkdir(parents=True, exist_ok=True)
    for directory in system_dirs:
        for entry in sorted(Path(directory).glob("*.desktop")):
            # The Settings panels (gnome-*-panel, NoDisplay) must stay: Settings lists its pages from them.
            if entry.stem not in KEEP_APPS and not entry.stem.endswith("-panel"):
                (target / entry.name).write_text("[Desktop Entry]\nType=Application\nHidden=true\n", encoding="utf-8")
    for name, icon in DEMO_LAUNCHERS:
        ident = f"demo.{icon}.desktop"
        (target / ident).write_text(
            f"[Desktop Entry]\nType=Application\nName={name}\nIcon={icon}\nExec=true\nCategories=Utility;\n",
            encoding="utf-8")


def fonts_conf(path, font_dirs, cache_dir):
    """fontconfig file: the system configuration plus the staged Google Sans Flex, own cache (no host font cache)."""
    dirs = "".join(f"  <dir>{d}</dir>\n" for d in font_dirs)
    path.write_text(f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
{dirs}  <cachedir>{cache_dir}</cachedir>
</fontconfig>
""", encoding="utf-8")
