"""Text samples shared by the bench clients.

GTK minimum widths depend on the script of the text (glyph advance, line breaking, fallback fonts), so every widget
whose width matters is exercised with one string per script: Latin, CJK and Arabic (right-to-left). No locale is
assumed: the strings are data, independent of the locale of the nested Shell (M3E_BENCH_LOCALE).
"""

LATIN = "Settings and files"
CJK = "設定とファイル"
ARABIC = "الإعدادات والملفات"
SCRIPTS = {"latin": LATIN, "cjk": CJK, "arabic": ARABIC}


def label(prefix, script):
    """A short caption such as 'tab 3 - <sample>' for the given script."""
    return f"{prefix} {SCRIPTS[script]}"


def cycle(prefix, index):
    """Caption for item `index`: the scripts alternate so that every list and tab bar mixes them."""
    names = list(SCRIPTS)
    return label(f"{prefix} {index}", names[index % len(names)])
