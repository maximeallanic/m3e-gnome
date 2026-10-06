"""measure.py picks the table of expected rows by toolkit: expected/ (shell), grid.py (GTK)."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

import cairo

HERE = Path(__file__).resolve().parent
BENCH_SHELL = HERE.parent
BENCH = BENCH_SHELL.parent / "m3e-bench"
sys.path.insert(0, str(BENCH_SHELL))
sys.path.insert(0, str(BENCH))
import expected  # noqa: E402
import grid  # noqa: E402
import measure  # noqa: E402

BACKGROUND = (0x80, 0x80, 0x80)       # witness under the bar
BAR = (0x18, 0x12, 0x0b)


def png(path, w, h, draw):
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    c = cairo.Context(s)
    c.set_source_rgb(*(v / 255 for v in BACKGROUND))
    c.paint()
    draw(c)
    s.write_to_png(str(path))


def bar(height):
    def d(c):
        c.set_source_rgb(*(v / 255 for v in BAR))
        c.rectangle(0, 0, 400, height)
        c.fill()
        # A few light "icons" in the bar.
        c.set_source_rgb(0.9, 0.9, 0.9)
        for x in (10, 190, 380):
            c.rectangle(x, 10, 12, 16)
            c.fill()
    return d


def write(folder, name, toolkit, cells, draw, w=400, h=136):
    (folder / f"layout-{name}.json").write_text(json.dumps({"toolkit": toolkit, "cells": cells}), encoding="utf-8")
    (folder / f"{name}-screen.json").write_text(json.dumps({"screen": {"scale": 1}}), encoding="utf-8")
    png(folder / f"{name}.png", w, h, draw)


class TestMeasureShell(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copy(HERE / "data" / "colors.css", self.d / "colors.css")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_table_by_toolkit(self):
        self.assertEqual(set(measure.rows_for_toolkit("shell")), {r.id for r in expected.ROWS})
        for tk in ("gtk3", "gtk4", "adw"):
            self.assertEqual(set(measure.rows_for_toolkit(tk)), {r.id for r in grid.ROWS})
        self.assertIsInstance(measure.rows_for_toolkit("shell")["witness-bar"], grid.Row)

    def test_witness_bar_conforming(self):
        cells = [{"row": "witness-bar", "state": "normal", "x": 0, "y": 0, "w": 400, "h": 136}]
        write(self.d, "shell-bar-normal", "shell", cells, bar(36))
        self.assertEqual(measure.main(self.d), 0)
        r = json.loads((self.d / "measurements.json").read_text(encoding="utf-8"))
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["toolkit"], r[0]["batch"], r[0]["row"]), ("shell", 2, "witness-bar"))
        self.assertEqual([d["key"] for d in r[0]["deviations"]], ["height"])
        self.assertAlmostEqual(r[0]["deviations"][0]["measured"], 36, delta=0.5)

    def test_witness_bar_deviation(self):
        cells = [{"row": "witness-bar", "state": "normal", "x": 0, "y": 0, "w": 400, "h": 136}]
        write(self.d, "shell-bar-normal", "shell", cells, bar(30))
        self.assertEqual(measure.main(self.d), 1)

    def test_gtk_row_unknown_to_shell(self):
        cells = [{"row": "button", "state": "normal", "x": 0, "y": 0, "w": 400, "h": 136}]
        write(self.d, "shell-bar-normal", "shell", cells, bar(36))
        with self.assertRaises(KeyError):
            measure.main(self.d)

    def test_gtk_unchanged(self):
        # GTK row (tooltip, batch 6): read from grid.ROWS, expected values of grid.py.
        def tooltip(c):
            c.set_source_rgb(0.2, 0.2, 0.3)
            c.rectangle(100, 50, 80, 24)
            c.fill()
        cells = [{"row": "tooltip", "state": "normal", "x": 80, "y": 30, "w": 120, "h": 64}]
        write(self.d, "gtk4-b6-p1", "gtk4", cells, tooltip)
        measure.main(self.d)
        r = json.loads((self.d / "measurements.json").read_text(encoding="utf-8"))
        self.assertEqual((r[0]["toolkit"], r[0]["batch"]), ("gtk4", 6))
        expected_state = {row.id: row for row in grid.ROWS}["tooltip"].expected["normal"]
        self.assertEqual({d["key"] for d in r[0]["deviations"]}, set(expected_state))

    def test_dark_palette_prefix(self):
        # "@dark.role" (lock screen, GDM): the neighbouring <out>/dark/colors.css is read under the "dark." prefix.
        out = self.d / "light"
        out.mkdir()
        shutil.copy(HERE / "data" / "colors.css", out / "colors.css")
        (self.d / "dark").mkdir()
        shutil.copy(HERE / "data" / "colors.css", self.d / "dark" / "colors.css")
        colors = measure.colors_for(out)
        self.assertEqual(colors["dark.on_surface"], colors["on_surface"])


if __name__ == "__main__":
    unittest.main()
