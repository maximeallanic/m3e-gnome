#!/usr/bin/env python3
"""Measures the captures of the bench and compares them with the tokens.

Usage: measure.py <folder>   (contains layout-<name>.json, <name>.png, <name>-screen.json, colors.css;
                              <name> = <toolkit>-b<batch>-p<page>)
Table of expected values chosen by toolkit: `expected.ROWS` (../m3e-bench-shell) for "shell", `grid.ROWS` otherwise.
Writes <folder>/measurements.json, prints a summary, exit code 0 if there is no deviation.
The palette of the measurement is <folder>/colors.css (copy recorded with the captures); it is never read from
the real home directory.
"""
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grid  # noqa: E402
from colors import delta_e2000, delta_e2000_lab, hexa, mix, read_colors, rgb_to_lab  # noqa: E402,F401
from measure_cell import Measurements, measure_cell  # noqa: E402,F401
from pixels import load, majority_edge, rect_in_image, region  # noqa: E402,F401

SHELL_BENCH = HERE.parent / "m3e-bench-shell"
TOKENS_JSON = HERE.parent / "reference" / "m3e-tokens.json"
TOLERANCE_PX = 1.0   # physical px
TOLERANCE_DE = 2.0   # deltaE2000


@dataclass
class Deviation:
    key: str
    expected: object
    measured: object
    ok: bool


def colors_for(folder):
    """Palette of the measurement: <folder>/colors.css (copy recorded with the captures).

    Shell style bench (<out>/<mode>/): the neighbouring dark palette (<out>/dark/colors.css) is added under the
    prefix "dark." (expected "@dark.role"): the lock screen and GDM are dark in both modes.
    """
    copy = Path(folder) / "colors.css"
    if not copy.exists():
        raise FileNotFoundError(f"no palette: {copy} (the bench records it next to its captures)")
    colors = read_colors(copy)
    dark = Path(folder).parent / "dark" / "colors.css"
    if dark.exists():
        colors.update({f"dark.{n}": c for n, c in read_colors(dark).items()})
    return colors


# --- comparison --------------------------------------------------------------------------------------------------

def _token(tokens, ref):
    comp, key = ref.split(".")
    return tokens[comp][key]


def _color(spec, tokens, colors, base):
    """Expected colour: "@role", colour token, or tuple (colour, opacity[, below]).

    Opacity: number, opacity token, or "@role" = the role's own opacity (translucent SystemUI roles,
    surface_effect_N, "--<role>-opacity" lines of the bench's colors.css). Below (optional): colour on which the mix
    is laid (default: the cell background)."""
    if isinstance(spec, tuple):
        c, op, *below = spec
        if isinstance(op, (int, float)):
            o = op
        elif op.startswith("@"):
            o = colors["opacity." + op[1:]]
        else:
            o = _token(tokens, op)["value"]
        if below:
            base = _color(below[0], tokens, colors, base)
        return mix(base, _color(c, tokens, colors, base), o)
    if spec.startswith("@"):
        return colors[spec[1:]]
    t = _token(tokens, spec)
    if t["type"] != "role":
        raise ValueError(f"{spec} is not a colour")
    return colors[t["value"]]


def _length(spec, tokens, scale):
    if isinstance(spec, (int, float)):
        return spec * scale
    return _token(tokens, spec)["value"] * scale


def _corner(spec, tokens, scale, m):
    """Expected radius of one corner: full shape (half the smallest measured side) or length."""
    if not isinstance(spec, (int, float)) and _token(tokens, spec)["type"] == "shape":
        return min(m.height, m.width) / 2
    return _length(spec, tokens, scale)


def compare(m, expected_state, row_expected, tokens, colors, scale, cell_background):
    deviations = []
    expected_background = None
    if "background" in expected_state:
        expected_background = _color(expected_state["background"], tokens, colors, cell_background)
    for key, spec in expected_state.items():
        if key in ("height", "width", "stroke"):
            a = _length(spec, tokens, scale)
            v = getattr(m, key)
            deviations.append(Deviation(key, round(a, 2), v, abs(v - a) <= TOLERANCE_PX))
        elif key == "radius":
            if isinstance(spec, list):
                # One corner per element (top-left, top-right, bottom-right, bottom-left): number, dp or full shape.
                a = [_corner(x, tokens, scale, m) for x in spec]
            else:
                t = None if isinstance(spec, (int, float)) else _token(tokens, spec)
                if t is not None and t["type"] == "shape":
                    a = [min(m.height, m.width) / 2] * 4
                elif t is not None and t["type"] == "corners":
                    a = [x * scale for x in t["value"]]
                else:
                    a = [_length(spec, tokens, scale)] * 4
            ok = all(abs(x - y) <= TOLERANCE_PX for x, y in zip(m.radius, a))
            deviations.append(Deviation(key, [round(x, 2) for x in a], m.radius, ok))
        elif key in ("background", "text"):
            base = cell_background if key == "background" else (expected_background or cell_background)
            a = _color(spec, tokens, colors, base)
            v = m.background if key == "background" else m.text
            de = delta_e2000(a, v)
            deviations.append(Deviation(key, hexa(a), f"{hexa(v)} (ΔE {de:.1f})", de < TOLERANCE_DE))
        elif key == "dominant":
            a = _color(spec, tokens, colors, cell_background)
            de = delta_e2000(a, m.dominant)
            deviations.append(Deviation(key, hexa(a), f"{hexa(m.dominant)} (ΔE {de:.1f})", de < TOLERANCE_DE))
        elif key == "layer":
            normal = row_expected.get("normal", {}).get("background")
            base = _color(normal, tokens, colors, cell_background) if normal else cell_background
            a = _color(spec, tokens, colors, base)
            de = delta_e2000(a, m.background)
            deviations.append(Deviation("background (layer)", hexa(a), f"{hexa(m.background)} (ΔE {de:.1f})",
                                        de < TOLERANCE_DE))
    return deviations


# --- program -----------------------------------------------------------------------------------------------------

def rows_for_toolkit(toolkit):
    """Table of expected values of the toolkit: Shell rows (`expected.ROWS` of the Shell bench) or GTK grid."""
    if toolkit == "shell":
        if str(SHELL_BENCH) not in sys.path:
            sys.path.insert(0, str(SHELL_BENCH))
        import expected  # noqa: E402
        return {r.id: r for r in expected.ROWS}
    return {r.id: r for r in grid.ROWS}


def _missing_capture(toolkit, row, cell):
    return {"toolkit": toolkit, "batch": row.batch, "row": cell["row"], "state": cell["state"],
            "deviations": [asdict(Deviation("capture", "image", "missing", False))]}


def main(folder):
    folder = Path(folder)
    tokens = json.loads(TOKENS_JSON.read_text(encoding="utf-8"))
    colors = colors_for(folder) if (folder / "colors.css").exists() else None
    results, total, ko = [], 0, 0
    for layout_file in sorted(folder.glob("layout-*.json")):
        layout = json.loads(layout_file.read_text(encoding="utf-8"))
        tk = layout["toolkit"]
        rows = rows_for_toolkit(tk)
        name = layout_file.stem[len("layout-"):]
        if not (folder / f"{name}.png").exists():
            for c in layout["cells"]:
                total, ko = total + 1, ko + 1
                results.append(_missing_capture(tk, rows[c["row"]], c))
            continue
        if colors is None:
            colors = colors_for(folder)   # raises with a clear message
        pb = load(folder / f"{name}.png")
        info = json.loads((folder / f"{name}-screen.json").read_text(encoding="utf-8"))
        scale = info.get("image_scale", info["screen"]["scale"])
        for c in layout["cells"]:
            rect = tuple(round(v * scale) for v in (c["x"], c["y"], c["w"], c["h"]))
            row = rows[c["row"]]
            if not rect_in_image(pb, rect):
                total, ko = total + 1, ko + 1
                results.append({"toolkit": tk, "batch": row.batch, "row": c["row"], "state": c["state"],
                                "image": f"{name}.png", "rect": rect,
                                "deviations": [asdict(Deviation("capture", "inside the screen", "outside capture",
                                                                False))]})
                continue
            cell_background = majority_edge(region(pb, rect))
            m = measure_cell(pb, rect, cell_background, **row.measure_options())
            expected_state = row.expected.get(c["state"], {})
            deviations = compare(m, expected_state, row.expected, tokens, colors, scale, cell_background)
            total += len(deviations)
            ko += sum(not d.ok for d in deviations)
            results.append({"toolkit": tk, "batch": row.batch, "row": c["row"], "state": c["state"],
                            "image": f"{name}.png", "rect": rect, "cell_background": hexa(cell_background),
                            "measurements": {**asdict(m), "background": hexa(m.background), "text": hexa(m.text),
                                             "dominant": hexa(m.dominant)},
                            "deviations": [asdict(d) for d in deviations]})
    (folder / "measurements.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    per_tk = Counter((r["toolkit"], d["ok"]) for r in results for d in r["deviations"])
    for tk in sorted({r["toolkit"] for r in results}):
        print(f"{tk:5} OK {per_tk[(tk, True)]:4}  DEVIATION {per_tk[(tk, False)]:4}")
    print(f"total OK {total - ko}  DEVIATION {ko}")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
