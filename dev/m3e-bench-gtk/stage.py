#!/usr/bin/env python3
"""Prepare, for one mode, everything the GTK bench needs OUTSIDE the nested Shell (run.sh calls it before nested.sh).

Usage: stage.py --out DIR --mode dark|light [--overrides DIR] [--base-theme DIR] [--extensions-repo DIR]
Writes, under DIR (the bench output directory of the mode):
  palette/            theme rendered by dev/m3e-bench/render_theme.py (fixed seed of theme/matugen/palette.json)
  stage/config/gtk-3.0, stage/config/gtk-4.0   the user GTK stacking (what the installer puts in ~/.config/gtk-*.css)
  stage/css/          the M3E stylesheets under test (copies: repository theme, or --overrides DIR, flat)
  stage/data/themes/Material-Gnome   copy of the base theme (read only source) + the palette of the mode
  stage/data/icons/Material-Symbols  link to the repository icon theme (read only)
  stage/extension/    the bench extension + logind-guard.js and tools.js copied from the extensions repository
  settings.keyfile    fixed neutral dconf settings of the applications (nothing read from the real session)
The extension installs stage/config and stage/data into the PRIVATE XDG directories of the nested Shell at enable().

GTK 4 stack (gtk.css and gtk-dark.css, same order as the installer): Material-Gnome gtk-4.0/<file>, m3e-gtk4-motion,
m3e-gtk4, window-buttons-gtk4, no-bold-gtk4, then the Ptyxis active-tab sheet. GTK 3 (gtk.css): m3e-gtk3 (which
imports its parts and the motion table), window-buttons-gtk3, no-bold-gtk3.
Bold is also removed from the copy of the theme's GTK 4 sheets, like the installer: they are imported at the same
priority as no-bold-gtk4.css, whose `*` rule would otherwise lose against their .title-1, .heading...
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "dev" / "m3e-bench"))
import render_theme  # noqa: E402

THEME = REPO / "theme"
PTYXIS_PALETTE = "gnome"                       # built into Ptyxis: fixed, independent of the user's profile
PTYXIS_PROFILE = "0123456789abcdef0123456789abcdef"   # neutral fixed profile uuid of the bench
OVERRIDE_FILES = ("m3e-gtk3*.css", "m3e-gtk4*.css", "no-bold-gtk3.css", "no-bold-gtk4.css",
                  "window-buttons-gtk3.css", "window-buttons-gtk4.css", "m3e-point-radio-symbolic.svg")
BOLD = re.compile(r"font-weight: *(bold|bolder|[6-9]00)")


def copy_overrides(css, overrides):
    css.mkdir(parents=True, exist_ok=True)
    if overrides:                                          # a flat install directory: every css and svg of it
        sources = [p for p in Path(overrides).iterdir() if p.suffix in (".css", ".svg")]
    else:
        sources = [p for pattern in OVERRIDE_FILES for p in (THEME / "overrides").glob(pattern)]
        sources += list((THEME / "motion" / "gtk").glob("m3e-gtk*-motion.css"))
    if not sources:
        raise SystemExit(f"stage.py: no stylesheet found ({overrides or THEME})")
    for p in sources:
        shutil.copy(p, css / p.name)
    # Chrome-only matugen output imported by window-buttons-gtk4.css: meaningless here, an empty file.
    (css / "chrome-dark-gtk4.css").write_text("", encoding="utf-8")


def stage_theme(stage, palette, base_theme):
    theme = stage / "data" / "themes" / "Material-Gnome"
    for sub in ("gtk-3.0", "gtk-4.0"):
        if not (base_theme / sub / "gtk.css").is_file():
            raise SystemExit(f"stage.py: base theme missing {base_theme}/{sub}/gtk.css (set M3E_BASE_THEME)")
        shutil.copytree(base_theme / sub, theme / sub)
    if (base_theme / "index.theme").is_file():
        shutil.copy(base_theme / "index.theme", theme / "index.theme")
    shutil.copy(palette / "colors-gtk3.css", theme / "gtk-3.0" / "colors.css")
    shutil.copy(palette / "colors-gtk4.css", theme / "gtk-4.0" / "colors.css")
    for sheet in (theme / "gtk-4.0").glob("gtk*.css"):
        sheet.write_text(BOLD.sub("font-weight: normal", sheet.read_text(encoding="utf-8")), encoding="utf-8")
    icons = stage / "data" / "icons"
    icons.mkdir(parents=True)
    (icons / "Material-Symbols").symlink_to(THEME / "icons" / "Material-Symbols")
    return theme


def ptyxis_sheet(css, out, overrides):
    """Active-tab sheet of Ptyxis for the fixed built-in palette; with --overrides, the one of the directory."""
    if overrides and (Path(overrides) / "ptyxis-active-tab.css").is_file():
        shutil.copy(Path(overrides) / "ptyxis-active-tab.css", css / "ptyxis-active-tab.css")
        return
    private = out / "ptyxis-xdg"                            # no palette of the real user is read
    for d in ("config", "data"):
        (private / d).mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "XDG_CONFIG_HOME": str(private / "config"), "XDG_DATA_HOME": str(private / "data")}
    subprocess.run([sys.executable, str(THEME / "bin" / "ptyxis-active-tab"), "--palette", PTYXIS_PALETTE,
                    "--output", str(css / "ptyxis-active-tab.css")], env=env, check=True, capture_output=True)


def write_stack(stage, theme, css, with_ptyxis):
    cfg4, cfg3 = stage / "config" / "gtk-4.0", stage / "config" / "gtk-3.0"
    cfg4.mkdir(parents=True)
    cfg3.mkdir(parents=True)
    for f in ("gtk.css", "gtk-dark.css"):
        imports = [theme / "gtk-4.0" / f, css / "m3e-gtk4-motion.css", css / "m3e-gtk4.css",
                   css / "window-buttons-gtk4.css", css / "no-bold-gtk4.css"]
        if with_ptyxis:
            imports.append(css / "ptyxis-active-tab.css")
        (cfg4 / f).write_text("".join(f'@import url("file://{p}");\n' for p in imports), encoding="utf-8")
    shutil.copy(theme / "gtk-4.0" / "colors.css", cfg4 / "colors.css")
    imports = [css / "m3e-gtk3.css", css / "window-buttons-gtk3.css", css / "no-bold-gtk3.css"]
    (cfg3 / "gtk.css").write_text("".join(f'@import url("file://{p}");\n' for p in imports), encoding="utf-8")


def write_settings(path, mode):
    """Fixed neutral settings of the applications (merged into the PRIVATE dconf by nested.sh --dconf-keyfile).
    Fonts keep the system defaults; the icon theme is the repository's Material-Symbols."""
    scheme = "prefer-dark" if mode == "dark" else "default"
    path.write_text(f"""[org/gnome/desktop/interface]
color-scheme='{scheme}'
gtk-theme='Material-Gnome'
icon-theme='Material-Symbols'
enable-animations=true
overlay-scrolling=true
enable-hot-corners=false
text-scaling-factor=1.0

[org/gnome/desktop/screensaver]
lock-enabled=false
idle-activation-enabled=false

[org/gnome/desktop/session]
idle-delay=uint32 0

[org/gnome/Ptyxis]
restore-session=false
restore-window-size=false
prompt-on-close=false
default-profile-uuid='{PTYXIS_PROFILE}'
profile-uuids=['{PTYXIS_PROFILE}']

[org/gnome/Ptyxis/Profiles/{PTYXIS_PROFILE}]
palette='{PTYXIS_PALETTE}'
use-custom-command=true
custom-command='bash --norc --noprofile'
login-shell=false
""", encoding="utf-8")


def stage_extension(stage, repo):
    """The bench extension plus logind-guard.js and tools.js of the extensions repository, copied now (not duplicated)."""
    src = HERE / "m3e-bench-gtk@maximeallanic.github.io"
    dst = stage / "extension"
    shutil.copytree(src, dst)
    shared = Path(repo) / "tests" / "bench" / "bench-extension" / "m3e-bench@maximeallanic.github.io"
    for name in ("logind-guard.js", "tools.js"):
        if not (shared / name).is_file():
            raise SystemExit(f"stage.py: {shared / name} not found (set M3E_EXTENSIONS_REPO)")
        shutil.copy(shared / name, dst / name)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", required=True)
    p.add_argument("--mode", required=True, choices=["dark", "light"])
    p.add_argument("--overrides")
    p.add_argument("--base-theme")
    p.add_argument("--extensions-repo", default=os.environ.get("M3E_EXTENSIONS_REPO") or str(REPO.parent / "m3e-gnome-extensions"))
    a = p.parse_args(argv)
    out = Path(a.out).resolve()
    base = Path(a.base_theme or os.environ.get("M3E_BASE_THEME") or Path.home() / ".themes" / "Material-Gnome")
    palette = render_theme.render(out / "palette", a.mode, base_theme=base)
    stage = out / "stage"
    if stage.exists():
        raise SystemExit(f"stage.py: {stage} already exists")
    theme = stage_theme(stage, palette, base)
    css = stage / "css"
    copy_overrides(css, a.overrides)
    ptyxis_sheet(css, out, a.overrides)
    write_stack(stage, theme, css, (css / "ptyxis-active-tab.css").is_file())
    write_settings(out / "settings.keyfile", a.mode)
    stage_extension(stage, a.extensions_repo)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
