#!/usr/bin/env python3
"""HTML comparison page: m3.material.io reference | GTK 3 | GTK 4 | libadwaita, then the deviations.

Usage: report.py <folder> [<reference_images_folder>]
Reads <folder>/measurements.json (measure.py) and the captures it points to, writes <folder>/report.html.
"""
import html
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid  # noqa: E402

DEFAULT_REFERENCES = Path(__file__).resolve().parent.parent / "reference" / "images"
TOOLKITS = ["gtk3", "gtk4", "adw"]
TOOLKIT_NAMES = {"gtk3": "GTK 3", "gtk4": "GTK 4", "adw": "libadwaita"}
COMPONENT = {
    "header": None,
    "button": "buttons", "button-suggested": "buttons", "button-destructive": "buttons", "button-flat": "buttons",
    "button-pill": "buttons", "toggle": "buttons", "adw-split": "buttons",
    "icon-button": "icon-buttons", "icon-button-flat": "icon-buttons",
    "switch": "switch", "checkbox": "checkbox", "radio": "radio-button",
    "entry": "text-fields", "spin-button": "text-fields", "dropdown": "text-fields",
    "adw-entry-row": "text-fields",
    "slider": "sliders", "progress": "progress-indicators",
    "menu": "menus", "tooltip": "tooltips", "dialog": "dialogs",
    "tabs": "tabs", "stack-switcher": "tabs", "sidebar": "navigation-drawer", "list": "lists",
}

STYLE = """
:root { --bg:#f7f7fa; --card:#ffffff; --text:#1b1b21; --soft:#5d5e67; --ok:#1e7a3c; --ko:#b3261e;
        --border:#d9d9e0; color-scheme: light dark; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
        --bg:#121318; --card:#1d1e24; --text:#e3e2e9; --soft:#a6a7b0; --ok:#7bd88f; --ko:#ffb4ab; --border:#33343a; } }
:root[data-theme="dark"] { --bg:#121318; --card:#1d1e24; --text:#e3e2e9; --soft:#a6a7b0; --ok:#7bd88f;
        --ko:#ffb4ab; --border:#33343a; }
body { margin:0; padding:16px; background:var(--bg); color:var(--text); font:14px/1.45 system-ui, sans-serif; }
h1 { font-size:22px; } h2 { font-size:18px; margin-top:32px; } h3 { font-size:15px; margin:20px 0 8px; }
.summary td, .summary th { padding:2px 10px; text-align:right; }
.gallery { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px; }
figure { margin:0; background:var(--card); border:1px solid var(--border); border-radius:12px; padding:8px; }
figure img { width:100%; height:auto; display:block; border-radius:6px; }
figcaption { color:var(--soft); font-size:12px; margin-top:4px; }
table.deviations { border-collapse:collapse; width:100%; margin-top:8px; font-size:12px; }
table.deviations td, table.deviations th { border-top:1px solid var(--border); padding:4px 6px; vertical-align:top; text-align:left; }
.deviation { display:block; } .deviation.ok { color:var(--ok); } .deviation.ko { color:var(--ko); font-weight:600; }
.others { font-size:12px; color:var(--soft); } .others a { color:inherit; }
.table { overflow-x:auto; }
"""


def thumbnail(png, rects, out, margin=6):
    """Crop of `png` around the union of `rects` (x, y, w, h), saved to `out`; None if the area is empty."""
    pb = GdkPixbuf.Pixbuf.new_from_file(str(png))
    x0 = max(0, min(r[0] for r in rects) - margin)
    y0 = max(0, min(r[1] for r in rects) - margin)
    x1 = min(pb.get_width(), max(r[0] + r[2] for r in rects) + margin)
    y1 = min(pb.get_height(), max(r[1] + r[3] for r in rects) + margin)
    if x1 <= x0 or y1 <= y0:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    pb.new_subpixbuf(x0, y0, x1 - x0, y1 - y0).savev(str(out), "png", [], [])
    return out


def component_references(reference_dir, component):
    """(main, others) reference images of a component: main = (path, caption) preferring a "states" view."""
    d = Path(reference_dir) / component
    if not d.is_dir():
        return None, []
    index = d / "index.tsv"
    entries = [e.split("\t", 1) for e in index.read_text(encoding="utf-8").splitlines()] if index.exists() else \
        [[p.name, p.stem] for p in sorted(d.glob("*.png"))]
    if not entries:
        return None, []
    main = next((e for e in entries if "state" in e[1].lower()), entries[0])
    return (d / main[0], main[1].strip()), [(d / n, a.strip()) for n, a in entries if n != main[0]]


def rel(path, base):
    return html.escape(os.path.relpath(path, base))


def _deviation_span(d):
    mark = "✓" if d["ok"] else "✗"
    return (f"<span class=\"deviation {'ok' if d['ok'] else 'ko'}\">{mark} "
            f"{html.escape(d['key'])}: {html.escape(str(d['measured']))} "
            f"<span class='others'>(expected {html.escape(str(d['expected']))})</span></span>")


def generate(folder, reference_images=DEFAULT_REFERENCES):
    folder = Path(folder)
    measurements = json.loads((folder / "measurements.json").read_text(encoding="utf-8"))
    by_row = defaultdict(list)
    for m in measurements:
        by_row[m["row"]].append(m)
    known = [r.id for r in grid.ROWS]
    order = [i for i in known if i in by_row] + sorted(set(by_row) - set(known))
    sections = defaultdict(list)
    for rid in order:
        sections[COMPONENT.get(rid) or "witnesses"].append(rid)

    count = Counter((m["toolkit"], d["ok"]) for m in measurements for d in m["deviations"])
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
             f"<title>M3 Expressive bench</title><style>{STYLE}</style></head><body>",
             f"<h1>M3 Expressive bench</h1><p class='others'>{html.escape(str(folder))}</p>",
             "<table class='summary'><tr><th></th><th>conforming</th><th>deviations</th></tr>"]
    for tk in TOOLKITS:
        if count[(tk, True)] or count[(tk, False)]:
            parts.append(f"<tr><th>{TOOLKIT_NAMES[tk]}</th><td>{count[(tk, True)]}</td><td>{count[(tk, False)]}</td></tr>")
    parts.append("</table>")

    for comp, rids in sections.items():
        parts.append(f'<section id="{html.escape(comp)}">' + f"<h2>{html.escape(comp)}</h2>")
        main, others = component_references(reference_images, comp) if comp != "witnesses" else (None, [])
        if main:
            parts.append(f"<div class='gallery'><figure><img src='{rel(main[0], folder)}' alt=''>"
                         f"<figcaption>Reference: {html.escape(main[1])}</figcaption></figure></div>")
        if others:
            links = " · ".join(f"<a href='{rel(p, folder)}'>{html.escape(a)}</a>" for p, a in others)
            parts.append(f"<p class='others'>Other views: {links}</p>")
        for rid in rids:
            entries = by_row[rid]
            parts.append(f"<h3>{html.escape(rid)}</h3><div class='gallery'>")
            for tk in TOOLKITS:
                with_image = [m for m in entries if m["toolkit"] == tk and m.get("image")]
                if not with_image or not (folder / with_image[0]["image"]).exists():
                    continue
                image = with_image[0]["image"]
                rects = [m["rect"] for m in with_image if m["image"] == image]
                v = thumbnail(folder / image, rects, folder / "thumbnails" / f"{tk}-{rid}.png")
                if v:
                    parts.append(f"<figure><img src='{rel(v, folder)}' alt=''>"
                                 f"<figcaption>{TOOLKIT_NAMES[tk]} — {' · '.join(grid.STATES)}</figcaption></figure>")
            parts.append("</div><div class='table'><table class='deviations'><tr><th>state</th>" +
                         "".join(f"<th>{TOOLKIT_NAMES[tk]}</th>" for tk in TOOLKITS) + "</tr>")
            for state in grid.STATES:
                cells = {tk: [m for m in entries if m["toolkit"] == tk and m["state"] == state] for tk in TOOLKITS}
                if not any(d for ms in cells.values() for m in ms for d in m["deviations"]):
                    continue
                parts.append(f"<tr><td>{state}</td>")
                for tk in TOOLKITS:
                    parts.append("<td>" + "".join(_deviation_span(d) for m in cells[tk] for d in m["deviations"])
                                 + "</td>")
                parts.append("</tr>")
            parts.append("</table></div>")
        parts.append("</section>")
    parts.append("</body></html>")
    out = folder / "report.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(generate(sys.argv[1], *(sys.argv[2:3] or [DEFAULT_REFERENCES])))
