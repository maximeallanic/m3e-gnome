#!/usr/bin/env python3
"""Check that the GTK stylesheets are wired to the motion base (GTK motion batch).

Usage: verify_springs.py <theme/motion/gtk> <m3e-gtk3.css> <m3e-gtk4.css>   (exit code 0 when conformant)
The two index files are followed through their relative `@import url("...")` lines: every part is checked on its own
and errors name the part and the line in it.
- GTK 4: every `transition` / `animation` only uses pairs
  `var(--m3e-spring-<name>-duration) var(--m3e-spring-<name>-curve)` of the same spring, defined in
  m3e-gtk4-motion.css; no duration or curve written literally (`none` accepted).
- GTK 3: every (duration, curve) pair is exactly the one of a spring of m3e-gtk3-motion.css (generated table), and the
  comment of the declaration names every spring used (`M3E.Spring.<Name>`); no keyword (ease, linear...).
"""
import re
import sys
from pathlib import Path

DECL = re.compile(r"(?<![-\w])(transition|animation)\s*:\s*([^;{}]*);\s*(/\*.*?\*/)?", re.S)
PAIR3 = re.compile(r"(\d+)ms\s+(cubic-bezier\([^)]*\))")
CLASS3 = re.compile(r"\.m3e-spring-[\w-]+\s*\{\s*transition-duration:\s*(\d+)ms;\s*/\*\s*M3E\.Spring\.(\w+)\s*\*/\s*"
                    r"transition-timing-function:\s*(cubic-bezier\([^)]*\));")
VAR4 = re.compile(r"--m3e-spring-([\w-]+?)-(duration|curve)\s*:")
PAIR4 = re.compile(r"var\(--m3e-spring-([\w-]+?)-duration\)\s+var\(--m3e-spring-([\w-]+?)-curve\)")
FORBIDDEN = re.compile(r"\b(ease|ease-in|ease-out|ease-in-out|linear|step-start|step-end)\b|\d+(\.\d+)?s\b")
IMPORT = re.compile(r'@import\s+url\(\s*["\']([^"\')]+)["\']\s*\)\s*;')


def strip_comments(t):
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), t, flags=re.S)


def norm(c):
    return re.sub(r"\s+", "", c)


def table3(text):
    return {(int(d), norm(c)): name for d, name, c in CLASS3.findall(text)}


def verify3(text, table, label="gtk3"):
    errors = []
    for m in DECL.finditer(text):
        prop, value, comment = m.group(1), m.group(2), m.group(3) or ""
        line = text.count("\n", 0, m.start()) + 1
        if value.strip() == "none":
            continue
        pairs = PAIR3.findall(value)
        if not pairs:
            errors.append(f"{label}:{line}: {prop} without a duration/curve pair of the base: {value.strip()[:60]}")
            continue
        rest = PAIR3.sub("", value)
        if FORBIDDEN.search(rest):
            errors.append(f"{label}:{line}: duration or curve outside the base: {value.strip()[:60]}")
        for duration, curve in pairs:
            name = table.get((int(duration), norm(curve)))
            if name is None:
                errors.append(f"{label}:{line}: {duration}ms {curve} is not a spring of the base")
            elif f"M3E.Spring.{name}" not in comment:
                errors.append(f"{label}:{line}: comment without M3E.Spring.{name}")
    return errors


def verify4(text, names, label="gtk4"):
    errors = []
    for m in DECL.finditer(strip_comments(text)):
        prop, value = m.group(1), m.group(2)
        line = text.count("\n", 0, m.start()) + 1
        if value.strip() == "none":
            continue
        if "cubic-bezier" in value or FORBIDDEN.search(PAIR4.sub("", value)) or re.search(r"\d+ms\b", value):
            errors.append(f"{label}:{line}: duration or curve written literally: {value.strip()[:60]}")
        pairs = PAIR4.findall(value)
        if not pairs:
            errors.append(f"{label}:{line}: {prop} without var(--m3e-spring-*)")
        for duration, curve in pairs:
            if duration != curve:
                errors.append(f"{label}:{line}: duration of {duration} and curve of {curve} mixed")
            elif duration not in names:
                errors.append(f"{label}:{line}: unknown spring: {duration}")
    return errors


def parts(index):
    """The index file and the files it imports (relative urls), in cascade order."""
    index = Path(index)
    found = [index]
    for target in IMPORT.findall(strip_comments(index.read_text(encoding="utf-8"))):
        part = index.parent / target
        if part.is_file():
            found.append(part)
    return found


def main(motion_dir, css3, css4):
    motion = Path(motion_dir)
    table = table3((motion / "m3e-gtk3-motion.css").read_text(encoding="utf-8"))
    names = {n for n, _ in VAR4.findall((motion / "m3e-gtk4-motion.css").read_text(encoding="utf-8"))}
    if len(table) < 6 or len(names) < 6:
        print("tables of the base unreadable", file=sys.stderr)
        return 2
    errors = []
    for part in parts(css3):
        errors += verify3(part.read_text(encoding="utf-8"), table, part.name)
    for part in parts(css4):
        errors += verify4(part.read_text(encoding="utf-8"), names, part.name)
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:]))
