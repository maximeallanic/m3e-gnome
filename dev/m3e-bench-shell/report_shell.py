#!/usr/bin/env python3
"""HTML page of the Shell style bench: per surface, reference m3.material.io | dark | light | deviations.

Usage: report_shell.py <folder> [<reference_images_folder>]
<folder> = output of run.sh: dark/ and light/ (measurements.json and captures from measure.py), both required.
Writes <folder>/report.html; exit code 1 if a mode is missing.
"""
import html, json, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "m3e-bench"))
import expected  # noqa: E402
from report import DEFAULT_REFERENCES, STYLE, component_references, rel, thumbnail  # noqa: E402

MODES = [("dark", "Dark"), ("light", "Light")]
# Surface -> reference image folder (dev/reference/images/<component>); None: no reference.
COMPONENT = {
    "bar": "icon-buttons",     # bar buttons: Standard icon button
    "base": "dialogs",         # base background of dialogs (surface_bright, SystemUI dialogs)
    "menu": "menus",           # Expressive vertical menu (same values as GTK)
    "settings": "buttons",     # tiles: Tonal button <-> Filled (toggle), split button
    "settings-menu": "lists",  # tile menu: M3E list items
    "calendar": "date-pickers",  # M3E Date picker (40 dp days, today = full primary)
    "notifications": "cards",    # notifications = Filled cards
    "notifications-buttons": "cards",
    "notifications-group": "cards",
    "banner": "cards",
    "previews": "tooltips",
    "search": "search",
    "grid": "lists",
    "folder": "dialogs",
    "page-dots": None,         # Pixel PagerDots (SystemUI): no M3E reference image
    "dialog-warning": "dialogs",  # warnings of the end-session dialog (error roles)
    "dialog": "dialogs",       # Dialog (28 dp, Headline small) in SystemUI colours, filled / outlined pill buttons
    "run-dialog": "text-fields",  # entry of the Run dialog = Filled text field
    "osd": "sliders",          # OSD level at the slider track (Pixel BrightnessSlider)
    "alttab": "lists",         # selected item secondary_container (List.ItemSelected*)
    "workspaces": "navigation-rail",  # active indicator secondary_container (active indicator pill)
    "tooltip": "tooltips",     # .dash-label = Plain tooltip
    "screenshot": "toolbars",  # panel = Floating toolbar; type choice = Connected button group (button-groups)
    "keyboard": "buttons",     # keys = Tonal buttons
    "lock": "icon-buttons",    # lock screen bar buttons; Display large clock (typography)
    "unlock": "text-fields",   # password entry = Filled text field
    "lock-media": "cards",     # lock screen media message = Filled card
    "lock-media-button": "cards",
    "login": "lists",          # user list = list items
    "login-prompt": "text-fields",  # password entry; cancel and session = Tonal icon buttons
}


def _deviations(entries):
    return "".join(
        f"<span class=\"deviation {'ok' if e['ok'] else 'ko'}\">{'✓' if e['ok'] else '✗'} "
        f"{html.escape(e['key'])}: {html.escape(str(e['measured']))} "
        f"<span class='others'>(expected {html.escape(str(e['expected']))})</span></span>"
        for m in entries for e in m["deviations"])


def generate(folder, reference_images=DEFAULT_REFERENCES):
    folder = Path(folder)
    missing = [m for m, _ in MODES if not (folder / m / "measurements.json").exists()]
    if missing:
        raise FileNotFoundError(f"mode(s) not measured: {', '.join(missing)} (dark/ and light/ required)")
    measurements = {m: json.loads((folder / m / "measurements.json").read_text(encoding="utf-8")) for m, _ in MODES}

    row_order = [r.id for r in expected.ROWS]
    by_surface = defaultdict(set)
    for ms in measurements.values():
        for x in ms:
            by_surface[expected.SURFACE.get(x["row"], "other")].add(x["row"])
    known = expected.surfaces_for()
    surface_order = [s for s in known if s in by_surface] + sorted(set(by_surface) - set(known))

    parts = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>"
             "<meta name='viewport' content='width=device-width, initial-scale=1'>"
             f"<title>Shell style bench</title><style>{STYLE}</style></head><body>",
             f"<h1>Shell style bench (M3 Expressive)</h1><p class='others'>{html.escape(str(folder))}</p>",
             "<table class='summary'><tr><th></th><th>conforming</th><th>deviations</th></tr>"]
    for m, name in MODES:
        c = Counter(e["ok"] for x in measurements[m] for e in x["deviations"])
        parts.append(f"<tr><th>{name}</th><td>{c[True]}</td><td>{c[False]}</td></tr>")
    parts.append("</table>")

    for surface in surface_order:
        rows = sorted(by_surface[surface], key=lambda r: (row_order.index(r) if r in row_order else 1e9, r))
        parts.append(f'<section id="{html.escape(surface)}"><h2>{html.escape(surface)}</h2><div class="gallery">')
        component = COMPONENT.get(surface)
        main, others = component_references(reference_images, component) if component else (None, [])
        if main:
            parts.append(f"<figure><img src='{rel(main[0], folder)}' alt=''>"
                         f"<figcaption>Reference: {html.escape(main[1])}</figcaption></figure>")
        # Captures: one thumbnail per mode and state (rectangles of the surface's cells).
        for m, name in MODES:
            by_image = defaultdict(list)
            for x in measurements[m]:
                if x["row"] in by_surface[surface] and x.get("image") and x.get("rect"):
                    by_image[(x["image"], x["state"])].append(x["rect"])
            for (image, state), rects in sorted(by_image.items(), key=lambda k: k[0][1]):
                if not (folder / m / image).exists():
                    continue
                t = thumbnail(folder / m / image, rects, folder / "thumbnails" / f"{m}-{surface}-{state}.png")
                if t:
                    parts.append(f"<figure><img src='{rel(t, folder)}' alt=''>"
                                 f"<figcaption>{name} — {html.escape(state)}</figcaption></figure>")
        parts.append("</div>")
        if others:
            links = " · ".join(f"<a href='{rel(p, folder)}'>{html.escape(a)}</a>" for p, a in others)
            parts.append(f"<p class='others'>Other views: {links}</p>")
        parts.append("<div class='table'><table class='deviations'><tr><th>row</th><th>state</th>" +
                     "".join(f"<th>{name}</th>" for _, name in MODES) + "</tr>")
        for row_id in rows:
            states = []
            for m, _ in MODES:
                for x in measurements[m]:
                    if x["row"] == row_id and x["state"] not in states:
                        states.append(x["state"])
            for state in states:
                parts.append(f"<tr><td>{html.escape(row_id)}</td><td>{html.escape(state)}</td>")
                for m, _ in MODES:
                    parts.append("<td>" + _deviations([x for x in measurements[m]
                                                       if x["row"] == row_id and x["state"] == state]) + "</td>")
                parts.append("</tr>")
        parts.append("</table></div></section>")
    parts.append("</body></html>")
    out = folder / "report.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def main(args):
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        generate(args[0], *(args[1:2]))
    except FileNotFoundError as e:
        print(f"report_shell.py: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
