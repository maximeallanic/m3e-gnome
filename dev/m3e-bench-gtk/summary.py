#!/usr/bin/env python3
"""Summary of the GTK bench: counts, per mode and per scenario, the "reported min width/height" warnings (negative
minimum sizes) and the CSS parsing errors of the journals, the expectations of the GTK 4 client ("checks" of
client4-data.json: handle sizes of the switch, back button...) that are not met, and links every widget address of the
GTK 4 client to its CSS path (client4-data.json).

Usage: summary.py <bench_out>   -> writes <out>/summary.json and prints a summary; exit code 0 when everything is zero.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

NEGATIVE = re.compile(r"(\w+) (0x[0-9a-f]+) \(([\w-]+)\) reported min (width|height) (-\d+)")
# GTK 3: negative sizes reported at allocation or at render time.
NEGATIVE3 = re.compile(r"(Negative content (?:width|height) -?\d+ \(allocation \d+, extents [^)]*\) while allocating gadget \(node ([\w-]+)|attempt to allocate widget with (?:width|height) -\d+)")
CSS = re.compile(r"(Theme parsing error|parsing-error|Error parsing|Gtk-WARNING.*\.css:\d+)")


def analyze_journal(text):
    """-> (Counter {(type, node, dimension): n}, [addresses], [CSS error lines])"""
    negatives, addresses = Counter(), []
    for m in NEGATIVE.finditer(text):
        negatives[(m.group(1), m.group(3), m.group(4))] += 1
        addresses.append(m.group(2))
    for m in NEGATIVE3.finditer(text):
        negatives[("gtk3", m.group(2) or "?", "allocation")] += 1
    errors = [line for line in text.splitlines() if CSS.search(line)]
    return negatives, addresses, errors


def main(root):
    root = Path(root)
    summary, total = {}, 0
    for mode in sorted(p for p in root.iterdir() if p.is_dir() and p.name in ("dark", "light")):
        paths, checks = {}, []
        if (mode / "client4-data.json").exists():
            data = json.loads((mode / "client4-data.json").read_text(encoding="utf-8"))
            paths, checks = data.get("addresses", {}), data.get("checks", [])
        for journal in sorted(mode.glob("journal-*.log")):
            neg, addresses, errors = analyze_journal(journal.read_text(encoding="utf-8", errors="replace"))
            n = sum(neg.values())
            unmet = [c for c in checks if not c["ok"]] if journal.stem == "journal-client4" else []
            total += n + len(errors) + len(unmet)
            summary[f"{mode.name}/{journal.stem[len('journal-'):]}"] = {
                "unmet_expectations": unmet,
                "negatives": n,
                "detail": {f"{t} ({node}) {dim}": c for (t, node, dim), c in neg.items()},
                "nodes": sorted({paths[a] for a in addresses if a in paths}),
                "css_errors": errors[:20],
            }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    for key, v in summary.items():
        state = "OK" if v["negatives"] == 0 and not v["css_errors"] and not v["unmet_expectations"] else "DEVIATION"
        print(f"{key:24} {state:9} negatives={v['negatives']:4} CSS errors={len(v['css_errors'])}"
              f" unmet expectations={len(v['unmet_expectations'])}"
              + (f"  {v['detail']}" if v["detail"] else "")
              + "".join(f"\n    {c['name']}: expected {c['expected']}, measured {c['measured']}"
                        for c in v["unmet_expectations"]))
    return 0 if total == 0 and summary else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
