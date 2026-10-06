#!/usr/bin/env python3
"""Converts the *Tokens.kt files of Compose Material3 (androidx) into m3e-tokens.json.

Usage: tokens.py <kt_folder> <output.json>
<kt_folder> holds the androidx.compose.material3 *Tokens.kt sources (not stored in this repository: fetch them from
the androidx repository, compose/material3/material3/src/commonMain/.../tokens/). Output schema, one entry per token:
  {Component: {Key: {"type": T, "value": V[, "source": "Object.Key"]}}}
  T = dp | sp | role (V = colour role, snake_case) | opacity | number | ms | curve (V = 4 floats) |
      shape (V = "full") | corners (V = 4 dp: top-start, top-end, bottom-end, bottom-start) | weight |
      typography (V = {"size", "line_height", "weight", "tracking"}).
Kotlin references (ShapeKeyTokens.CornerMedium, TypographyKeyTokens.LabelLarge...) are resolved to their value;
`source` keeps the name they were written with. Lines that cannot be converted are listed on stderr.
"""
import json
import re
import sys
from pathlib import Path

NUMBER = r"-?\d+(?:\.\d+)?"
WEIGHTS = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Normal": 400, "Medium": 500,
           "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900}


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _raw(name, value, const):
    """Kotlin value -> typed dict, or reference {"ref": "Object.Key"} to resolve, or None."""
    value = re.sub(r"//[^\n]*", "", value)
    v = re.sub(r"\s+", "", value).rstrip(",")
    if m := re.fullmatch(rf"({NUMBER})\.dp", v):
        return {"type": "dp", "value": float(m[1])}
    if m := re.fullmatch(rf"({NUMBER})\.sp", v):
        return {"type": "sp", "value": float(m[1])}
    if m := re.fullmatch(r"ColorSchemeKeyTokens\.(\w+)", v):
        return {"type": "role", "value": snake(m[1])}
    if m := re.fullmatch(r"CubicBezierEasing\((.*)\)", v):
        return {"type": "curve", "value": [float(x.rstrip("f")) for x in m[1].split(",")]}
    if v == "RectangleShape":
        return {"type": "dp", "value": 0.0}
    if v == "CircleShape":
        return {"type": "shape", "value": "full"}
    if m := re.fullmatch(rf"(?:RoundedCornerShape|CornerSize)\(({NUMBER})\.dp\)", v):
        return {"type": "dp", "value": float(m[1])}
    if m := re.fullmatch(r"RoundedCornerShape\((.*)\)", v):
        corners = dict(re.findall(rf"(\w+)=({NUMBER})\.dp", m[1]))
        if len(corners) == 4:
            return {"type": "corners", "value": [float(corners[k]) for k in
                                                 ("topStart", "topEnd", "bottomEnd", "bottomStart")]}
        return None
    if m := re.fullmatch(r"FontWeight\.(\w+)", v):
        return {"type": "weight", "value": WEIGHTS[m[1]]} if m[1] in WEIGHTS else None
    if m := re.fullmatch(r"(ShapeKey|Shape|Elevation|TypographyKey|Typeface)Tokens\.(\w+)", v):
        return {"ref": f"{m[1]}Tokens.{m[2]}"}
    if const and (m := re.fullmatch(rf"({NUMBER})f?", v)):
        x = float(m[1])
        if "Opacity" in name:
            return {"type": "opacity", "value": x}
        if name.startswith("Duration"):
            return {"type": "ms", "value": x}
        return {"type": "number", "value": x}
    return None


def parse_kt(text):
    """Text of a *Tokens.kt file -> {Key: raw value} (references not resolved)."""
    # Two-line getter: "inline val X: Type \n [inline] get() = V" -> "val X = V"
    text = re.sub(r":\s*[\w.<>?]+\s*\n\s*(?:inline\s+)?get\(\)\s*=", " =", text)
    body = text[text.find("internal object"):] if "internal object" in text else text
    decl = re.compile(r"^\s*(const\s+)?(?:inline\s+)?val\s+(\w+)\s*=\s*(.*?)(?=^\s*(?:const\s+|inline\s+)?val\s|^\})",
                      re.S | re.M)
    out = {}
    for const, name, value in decl.findall(body):
        b = _raw(name, value, bool(const))
        if b is None:
            print(f"ignored: {name} = {' '.join(value.split())[:60]}", file=sys.stderr)
        else:
            out[name] = b
    return out


def resolve(raw):
    """{Component: {Key: raw}} -> same keys, references replaced by their values."""
    def target(ref):
        obj, key = ref.split(".")
        if obj == "ShapeKeyTokens":
            obj = "ShapeTokens"
        if obj == "TypographyKeyTokens":
            ts = raw.get("TypeScale", {})
            weight = resolve_one(ts.get(key + "Weight"))
            return {"type": "typography", "value": {
                "size": ts[key + "Size"]["value"], "line_height": ts[key + "LineHeight"]["value"],
                "weight": weight["value"] if weight else None,
                "tracking": ts[key + "Tracking"]["value"] if key + "Tracking" in ts else 0.0}}
        return resolve_one(raw.get(obj[:-len("Tokens")], {}).get(key))

    def resolve_one(b):
        if b is None or "ref" not in b:
            return b
        r = target(b["ref"])
        return None if r is None else {**r, "source": b["ref"]} if b["ref"].split(".")[0] != "TypefaceTokens" else r

    out = {}
    for comp, keys in raw.items():
        out[comp] = {}
        for key, b in keys.items():
            r = resolve_one(b)
            if r is None:
                print(f"unresolved reference: {comp}.{key} -> {b.get('ref')}", file=sys.stderr)
            else:
                out[comp][key] = r
    return out


def main(folder, output):
    raw = {p.name[:-len("Tokens.kt")]: parse_kt(p.read_text(encoding="utf-8"))
           for p in sorted(Path(folder).glob("*Tokens.kt"))}
    Path(output).write_text(json.dumps(resolve(raw), indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                            encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
