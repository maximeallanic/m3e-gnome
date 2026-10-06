#!/usr/bin/env python3
"""Render the m3e-gnome theme templates into a private directory, for the benches.

The theme renders through matugen with theme/matugen/config.toml, whose paths point into the real home directory
(~/.config/m3e-gnome, ~/.themes) and whose post hooks change the session (gsettings, papirus-folders). The benches
never use that file as is: this script reads it, keeps only the colour templates (GTK colours), the Shell parts and
the extensions sheet, remaps every input to the repository (or to the base theme, read only) and every output to
OUT, drops every hook, refuses a sandboxed config that would write outside OUT, then runs material-palette
(tools/material-palette: 2025 colour spec) with that config. Nothing is written outside OUT.

Usage: render_theme.py --out DIR --mode dark|light [--seed #rrggbb] [--base-theme DIR] [--theme-root DIR]
Writes: DIR/palette.json, DIR/matugen.toml (the sandboxed config), DIR/shell/NN-*.css (rendered parts),
        DIR/gnome-shell.css (parts concatenated in index order, like the theme's post hook),
        DIR/colors-gtk3.css, DIR/colors-gtk4.css, DIR/m3e-extensions.css.
The seed defaults to fallback_color of theme/matugen/palette.json (reproducible palette, independent of the wallpaper).
The base theme (Material-Gnome, default ~/.themes/Material-Gnome or $M3E_BASE_THEME) is only read.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KEPT = re.compile(r"^(gtk3|gtk4|shell-\d\d-.+|m3e-extensions)$")
ALLOWED_KEYS = {"input_path", "output_path"}


def _expand(path, home="~"):
    return str(path).replace("~", home, 1) if str(path).startswith("~") else str(path)


def map_input(path, theme_root, base_theme):
    """Real-home input path of the theme config -> file in the repository (or in the base theme)."""
    p = str(path)
    for prefix, target in (
        ("~/.config/m3e-gnome/shell/", theme_root / "shell" / "m3e-shell"),
        ("~/.config/m3e-gnome/overrides/", theme_root / "overrides"),
        ("~/.themes/Material-Gnome/", base_theme),
    ):
        if p.startswith(prefix):
            return target / p[len(prefix):]
    if p == "~/.config/m3e-gnome/m3e-extensions-template.css":
        return theme_root / "shell" / "m3e-extensions-template.css"
    raise ValueError(f"input path with no known mapping: {p}")


def map_output(name, path, out):
    """Output path of the theme config -> file inside OUT."""
    base = Path(str(path)).name
    if name == "gtk3":
        return out / "colors-gtk3.css"
    if name == "gtk4":
        return out / "colors-gtk4.css"
    if name.startswith("shell-"):
        return out / "shell" / base
    return out / base


def sandbox_config(config_toml, out, theme_root, base_theme):
    """Return (toml text, [(name, output Path)]) for the sandboxed config."""
    c = tomllib.loads(Path(config_toml).read_text(encoding="utf-8"))
    templates = {n: t for n, t in c.get("templates", {}).items() if KEPT.match(n)}
    if not templates:
        raise ValueError("no template kept: is this the m3e-gnome matugen config?")
    lines = ["[config]", "version_check = false", ""]
    outputs = []
    for name, t in templates.items():
        src = map_input(t["input_path"], theme_root, base_theme)
        dst = map_output(name, t["output_path"], out)
        outputs.append((name, dst))
        for p in (src, dst):
            if '"' in str(p) or "\\" in str(p):
                raise ValueError(f"unsupported path: {p}")
        lines += [f"[templates.{name}]", f'input_path = "{src}"', f'output_path = "{dst}"', ""]
    text = "\n".join(lines)
    check_sandbox(text, out)
    return text, outputs


def check_sandbox(text, out):
    """Raise ValueError unless the config only has input/output paths and writes inside OUT."""
    c = tomllib.loads(text)
    if set(c) - {"config", "templates"}:
        raise ValueError(f"unexpected sections: {sorted(set(c) - {'config', 'templates'})}")
    if set(c.get("config", {})) - {"version_check"}:
        raise ValueError(f"unexpected settings: {sorted(set(c['config']) - {'version_check'})}")
    root = Path(out).resolve()
    for name, t in c.get("templates", {}).items():
        if set(t) != ALLOWED_KEYS:
            raise ValueError(f"{name}: forbidden or missing keys: {sorted(set(t) ^ ALLOWED_KEYS)}")
        if root not in Path(t["output_path"]).resolve().parents:
            raise ValueError(f"{name} writes outside {root}: {t['output_path']}")


def concatenate_shell_parts(config_toml, out):
    """DIR/gnome-shell.css = rendered shell parts in cascade (index) order, like the post hook of the theme."""
    c = tomllib.loads(Path(config_toml).read_text(encoding="utf-8"))
    parts = sorted(((t.get("index", 0), n) for n, t in c["templates"].items() if n.startswith("shell-")))
    chunks = []
    for _, name in parts:
        chunks.append((out / "shell" / f"{name[len('shell-'):]}.css").read_text(encoding="utf-8"))
    (out / "gnome-shell.css").write_text("".join(chunks), encoding="utf-8")


def render(out, mode, seed=None, base_theme=None, theme_root=None):
    out = Path(out).resolve()
    theme_root = Path(theme_root or REPO / "theme")
    base_theme = Path(base_theme or os.environ.get("M3E_BASE_THEME") or Path.home() / ".themes" / "Material-Gnome")
    palette_config = theme_root / "matugen" / "palette.json"
    seed = seed or json.loads(palette_config.read_text(encoding="utf-8"))["fallback_color"]
    (out / "shell").mkdir(parents=True, exist_ok=True)
    text, outputs = sandbox_config(theme_root / "matugen" / "config.toml", out, theme_root, base_theme)
    (out / "matugen.toml").write_text(text, encoding="utf-8")
    # Private XDG directories: nothing of the real home configuration can be read or written by the tools.
    private = out / "xdg"
    env = {**os.environ, "MATERIAL_PALETTE_CONFIG": str(palette_config),
           "XDG_CONFIG_HOME": str(private / "config"), "XDG_CACHE_HOME": str(private / "cache"),
           "XDG_DATA_HOME": str(private / "data"), "XDG_STATE_HOME": str(private / "state")}
    for d in ("config", "cache", "data", "state"):
        (private / d).mkdir(parents=True, exist_ok=True)
    cmd = [str(theme_root / "bin" / "material-palette"), "--color", seed, "--mode", mode,
           "--json", str(out / "palette.json"), "--matugen-config", str(out / "matugen.toml")]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"material-palette ({mode}) failed: {r.stderr.strip() or r.stdout.strip()}")
    for name, dst in outputs:
        if not dst.is_file() or dst.stat().st_size == 0:
            raise RuntimeError(f"matugen produced no {dst}")
    concatenate_shell_parts(out / "matugen.toml", out)
    return out


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", required=True)
    p.add_argument("--mode", required=True, choices=["dark", "light"])
    p.add_argument("--seed")
    p.add_argument("--base-theme")
    p.add_argument("--theme-root")
    a = p.parse_args(argv)
    try:
        render(a.out, a.mode, a.seed, a.base_theme, a.theme_root)
    except (ValueError, RuntimeError, tomllib.TOMLDecodeError, KeyError, OSError) as e:
        print(f"render_theme: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
