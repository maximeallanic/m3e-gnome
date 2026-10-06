#!/usr/bin/env python3
"""Prepare, for one mode and one wallpaper, everything the screenshot session needs OUTSIDE the nested Shell.

Usage: stage.py --out DIR --mode dark|light [--wallpaper dunes|ocean|dusk|forest] [--icons-src DIR]
                [--font-dir DIR] [--mono-font-dir DIR] [--stock-gtk] [--seed-from-image] [--base-theme DIR] [--extensions-repo DIR]
Writes, under DIR (nothing outside it; the real home, dconf and ~/.config are only read, never written):
  wallpaper.png         the generated wallpaper (wallpapers.py, CC0)
  palette/              the theme rendered with the seed of the wallpaper (pinned, see wallpapers.SEEDS)
  stage/gnome-shell.css the rendered Shell theme (loaded by the m3e-shots extension, like user-theme)
  stage/data/           XDG_DATA_DIRS entry: themes/Material-Gnome, icons/ (Material-Symbols + Papirus), applications/
  stage/overlay/        config and data copied by the extension into the nested Shell's private XDG directories
  stage/fonts.conf      fontconfig file (Google Sans Flex copy), exported as FONTCONFIG_FILE
  stage/ext/            m3e-gnome-extensions installed with its own scripts/install.sh --dest
  home/demo/            fake home (demohome.py)
  settings.keyfile      dconf settings of the session (merged into the PRIVATE dconf by nested.sh)
  env.sh                `export` lines for capture.sh (XDG_DATA_DIRS, FONTCONFIG_FILE, HOME, USER...)
Needs: the installed Material-Gnome base theme and Papirus icons (see README.md), material-palette, matugen, Pillow.
"""
import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "dev" / "m3e-bench"))
sys.path.insert(0, str(HERE))
import demohome  # noqa: E402
import render_theme  # noqa: E402
import wallpapers  # noqa: E402

THEME = REPO / "theme"
ACCENTS = {"blue": "#3584e4", "teal": "#2190a4", "green": "#3a944a", "yellow": "#c88800", "orange": "#ed5b00",
           "red": "#e62d42", "pink": "#d56199", "purple": "#9141ac", "slate": "#6f8396"}
SYMBOLS_LINKS = ("Papirus", "Papirus-Dark", "Papirus-Symbolic", "Googlebook")   # read-only links to the installed ones


def gtk_bench():
    """The GTK bench's stage.py (theme copy, GTK 3/4 override stacks), loaded under another module name."""
    spec = importlib.util.spec_from_file_location("gtk_bench_stage", REPO / "dev" / "m3e-bench-gtk" / "stage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_color(image, mode, work):
    """Seed colour of an image, as material-sync computes it (material-palette --image)."""
    out = work / "seed.json"
    subprocess.run(["material-palette", "--image", str(image), "--mode", mode, "--json", str(out)],
                   check=True, capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))["colors"]["source_color"]["default"]["hex"]


def _lab(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    x = 0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = 0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x / 0.95047, y, z / 1.08883)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def accent_for(primary_hex):
    """GNOME accent preset nearest to the primary colour (what the theme's gnome-accent entry sets)."""
    target = _lab(primary_hex)
    return min(ACCENTS, key=lambda name: math.dist(target, _lab(ACCENTS[name])))


def render_ptyxis(palette_dir, target):
    """Ptyxis "Material" palette: the ptyxis entry of theme/matugen/config.toml, rendered from palette.json."""
    toml = palette_dir / "ptyxis.toml"
    toml.write_text(f'[config]\nversion_check = false\n\n[templates.ptyxis]\n'
                    f'input_path = "{THEME / "overrides" / "ptyxis-material.palette"}"\noutput_path = "{target}"\n',
                    encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    private = palette_dir / "xdg"
    env = {**os.environ, "XDG_CONFIG_HOME": str(private / "config"), "XDG_CACHE_HOME": str(private / "cache")}
    subprocess.run(["matugen", "--config", str(toml), "--quiet", "json", str(palette_dir / "palette.json")],
                   check=True, capture_output=True, env=env)


def stage_icons(data, icons_src):
    """icons/: Material-Symbols copied (its relative links need Papirus-Dark next to it) + links to the installed Papirus."""
    icons = data / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copytree(THEME / "icons" / "Material-Symbols", icons / "Material-Symbols", symlinks=True)
    for name in SYMBOLS_LINKS:
        source = Path(icons_src) / name
        if not source.is_dir():
            raise SystemExit(f"stage.py: {source} not found (run install.sh, or pass --icons-src)")
        (icons / name).symlink_to(source)
    subprocess.run(["gtk-update-icon-cache", "-q", "-f", str(icons / "Material-Symbols")], check=False)


def stage_driver(repo, stage):
    """The capture extension plus logind-guard.js and tools.js of the extensions repository (copied, not duplicated)."""
    dst = stage / "ext-shots"
    shutil.copytree(HERE / "m3e-shots@maximeallanic.github.io", dst)
    shared = Path(repo) / "tests" / "bench" / "bench-extension" / "m3e-bench@maximeallanic.github.io"
    for name in ("logind-guard.js", "tools.js"):
        if not (shared / name).is_file():
            raise SystemExit(f"stage.py: {shared / name} not found (set M3E_EXTENSIONS_REPO)")
        shutil.copy(shared / name, dst / name)


def write_settings(path, mode, accent, wallpaper):
    # "default" would make the Shell load its DARK stock sheet (GNOME 48+); prefer-light selects the light one, which the
    # light palette of the theme is written against.
    scheme = "prefer-dark" if mode == "dark" else "prefer-light"
    favorites = ", ".join(f"'{a}'" for a in demohome.FAVORITES)
    path.write_text(f"""[org/gnome/desktop/interface]
color-scheme='{scheme}'
gtk-theme='Material-Gnome'
icon-theme='Material-Symbols'
cursor-theme='Googlebook'
cursor-size=24
font-name='Google Sans Flex 10.5'
monospace-font-name='Adwaita Mono 11'
document-font-name='Adwaita Sans 12'
accent-color='{accent}'
clock-format='24h'
clock-show-weekday=true
enable-animations=true
enable-hot-corners=false
overlay-scrolling=true
text-scaling-factor=1.0

[org/gnome/desktop/wm/preferences]
button-layout='appmenu:minimize,maximize,close'

[org/gnome/desktop/background]
picture-uri='file://{wallpaper}'
picture-uri-dark='file://{wallpaper}'
picture-options='zoom'

[org/gnome/desktop/screensaver]
lock-enabled=false
idle-activation-enabled=false

[org/gnome/desktop/session]
idle-delay=uint32 0

[org/gnome/desktop/sound]
event-sounds=false

[org/gnome/shell]
favorite-apps=[{favorites}]

[org/gnome/Ptyxis]
interface-style='system'
restore-session=false
restore-window-size=false
prompt-on-close=false
default-profile-uuid='0123456789abcdef0123456789abcdef'
profile-uuids=['0123456789abcdef0123456789abcdef']

[org/gnome/Ptyxis/Profiles/0123456789abcdef0123456789abcdef]
palette='material'
use-custom-command=true
custom-command='bash --norc --noprofile'
login-shell=false
""", encoding="utf-8")


def install_extensions(repo, dest):
    subprocess.run(["bash", str(Path(repo) / "scripts" / "install.sh"), "--dest", str(dest)],
                   check=True, capture_output=True)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", required=True)
    p.add_argument("--mode", required=True, choices=["dark", "light"])
    p.add_argument("--wallpaper", default="dunes", choices=sorted(wallpapers.SCENES))
    p.add_argument("--icons-src", default=str(Path.home() / ".local/share/icons"))
    p.add_argument("--font-dir", default=str(Path.home() / ".local/share/fonts/GoogleSansFlex"))
    p.add_argument("--mono-font-dir", default=str(Path.home() / ".local/share/fonts/adwaita-mono"))
    p.add_argument("--seed-from-image", action="store_true",
                   help="derive the seed from the wallpaper instead of the pinned one (the quantizer is randomised)")
    p.add_argument("--stock-gtk", action="store_true",
                   help="write no GTK 3/4 user stylesheet (stock libadwaita look, to tell theme defects from stock behaviour)")
    p.add_argument("--base-theme")
    p.add_argument("--extensions-repo",
                   default=os.environ.get("M3E_EXTENSIONS_REPO") or str(REPO.parent / "m3e-gnome-extensions"))
    a = p.parse_args(argv)
    out = Path(a.out).resolve()
    if out.exists():
        raise SystemExit(f"stage.py: {out} already exists")
    out.mkdir(parents=True)
    base = Path(a.base_theme or os.environ.get("M3E_BASE_THEME") or Path.home() / ".themes" / "Material-Gnome")
    wall = out / "wallpaper.png"
    wallpapers.scene(a.wallpaper, (1920, 1080)).save(wall)
    seed = source_color(wall, a.mode, out) if a.seed_from_image else wallpapers.SEEDS[a.wallpaper]
    palette = render_theme.render(out / "palette", a.mode, seed=seed, base_theme=base)
    primary = json.loads((palette / "palette.json").read_text(encoding="utf-8"))["colors"]["primary"]["default"]["hex"]

    stage = out / "stage"
    gtk = gtk_bench()
    theme = gtk.stage_theme(stage, palette, base)           # stage/data/themes/Material-Gnome (+ an icons link, replaced)
    shutil.rmtree(stage / "data" / "icons")
    css = stage / "css"
    gtk.copy_overrides(css, None)
    gtk.write_stack(stage, theme, css, False)               # stage/config/gtk-{3,4}.0
    overlay = stage / "overlay"
    shutil.move(stage / "config", overlay / "config")
    if a.stock_gtk:
        shutil.rmtree(overlay / "config" / "gtk-3.0")
        shutil.rmtree(overlay / "config" / "gtk-4.0")
    (overlay / "config" / "m3e-gnome").mkdir()
    shutil.copy(palette / "m3e-extensions.css", overlay / "config" / "m3e-gnome" / "m3e-extensions.css")
    home = out / "home" / "demo"
    home.mkdir(parents=True)
    (overlay / "config" / "user-dirs.dirs").write_text(demohome.user_dirs(), encoding="utf-8")
    render_ptyxis(palette, overlay / "data" / "org.gnome.Ptyxis" / "palettes" / "material.palette")
    shutil.copy(palette / "gnome-shell.css", stage / "gnome-shell.css")

    stage_icons(stage / "data", a.icons_src)
    demohome.make_applications(stage / "data" / "applications")
    demohome.make_home(home)
    fonts = stage / "fonts"
    shutil.copytree(a.font_dir, fonts / "GoogleSansFlex")
    # Adwaita Mono: the terminal font (GNOME default); regular and italic only, they are all the demo uses.
    (fonts / "AdwaitaMono").mkdir()
    for style in ("Regular", "Italic"):
        shutil.copy(Path(a.mono_font_dir) / f"AdwaitaMono-{style}.ttf", fonts / "AdwaitaMono")
    demohome.fonts_conf(stage / "fonts.conf", [fonts], stage / "fc-cache")
    install_extensions(a.extensions_repo, stage / "ext")
    stage_driver(a.extensions_repo, stage)
    write_settings(out / "settings.keyfile", a.mode, accent_for(primary), wall)
    (out / "env.sh").write_text(
        f'export HOME="{home}" USER=demo LOGNAME=demo\n'
        f'export XDG_DATA_DIRS="{stage / "data"}:/usr/local/share:/usr/share"\n'
        f'export FONTCONFIG_FILE="{stage / "fonts.conf"}"\n'
        f'export M3E_SHOTS_STAGE="{stage}"\n', encoding="utf-8")
    print(f"staged {a.mode}/{a.wallpaper}: seed {seed}, accent {accent_for(primary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
