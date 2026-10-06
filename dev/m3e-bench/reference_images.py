#!/usr/bin/env python3
"""Downloads the images of the "specs" pages of m3.material.io (rendered by headless Chrome).

Usage: reference_images.py <images_folder> [component ...]
Without a component name, every component of COMPONENTS is fetched. For each component, writes
<images_folder>/<component>/NN-<alt-text-slug>.<ext> and <images_folder>/<component>/index.tsv ("file<TAB>alt text"),
which report.py reads to show the reference next to the measured widgets (default folder: dev/reference/images).
Needs network access and `google-chrome` on PATH; it opens no window (--headless=new, throw-away profile) and
touches nothing outside <images_folder>.
"""
import html
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

COMPONENTS = ["buttons", "icon-buttons", "switch", "checkbox", "radio-button", "sliders", "progress-indicators",
              "text-fields", "menus", "tooltips", "dialogs", "tabs", "navigation-rail", "navigation-drawer", "lists",
              "search", "date-pickers", "cards", "toolbars", "button-groups"]


def extract(page):
    """Rendered HTML -> [(alt text, full-resolution URL)] of the illustrations (lh3.googleusercontent.com)."""
    out = []
    for tag in re.findall(r"<img[^>]*>", page):
        src = re.search(r'src="([^"]+)"', tag)
        if not src or "lh3.googleusercontent.com" not in src[1]:
            continue
        alt = re.search(r'alt="([^"]*)"', tag)
        url = re.sub(r"=[^/=]*$", "", html.unescape(src[1])) + "=s0"
        out.append((html.unescape(alt[1]) if alt else "", url))
    return out


def file_name(rank, alt):
    slug = re.sub(r"[^a-z0-9]+", "-", alt.lower()).strip("-")[:60].rstrip("-") or "image"
    return f"{rank:02d}-{slug}"


def render(url):
    with tempfile.TemporaryDirectory() as profile:
        r = subprocess.run(["google-chrome", "--headless=new", f"--user-data-dir={profile}",
                            "--virtual-time-budget=15000", "--dump-dom", url],
                           capture_output=True, text=True, timeout=120)
    return r.stdout


def download(folder, component):
    page = render(f"https://m3.material.io/components/{component}/specs")
    target = Path(folder) / component
    target.mkdir(parents=True, exist_ok=True)
    names = []
    for rank, (alt, url) in enumerate(extract(page), 1):
        with urllib.request.urlopen(url, timeout=60) as response:
            ext = {"image/png": "png", "image/webp": "webp", "image/jpeg": "jpg",
                   "image/gif": "gif"}.get(response.headers.get_content_type(), "png")
            name = f"{file_name(rank, alt)}.{ext}"
            (target / name).write_bytes(response.read())
        names.append((name, alt))
    (target / "index.tsv").write_text("".join(f"{n}\t{a}\n" for n, a in names), encoding="utf-8")
    return names


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for c in sys.argv[2:] or COMPONENTS:
        print(c, len(download(sys.argv[1], c)))
