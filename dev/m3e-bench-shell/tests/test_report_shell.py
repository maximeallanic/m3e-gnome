"""report_shell.py: one section per surface (reference | dark | light | deviations of both modes)."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

import cairo

HERE = Path(__file__).resolve().parent
BENCH_SHELL = HERE.parent
sys.path.insert(0, str(BENCH_SHELL))
import expected  # noqa: E402
import report_shell  # noqa: E402


def png(path, color):
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, 400, 136)
    c = cairo.Context(s)
    c.set_source_rgb(0.5, 0.5, 0.5)
    c.paint()
    c.set_source_rgb(*color)
    c.rectangle(0, 0, 400, 36)
    c.fill()
    s.write_to_png(str(path))


def measurement(ok, height):
    return {"toolkit": "shell", "batch": 2, "row": "witness-bar", "state": "normal",
            "image": "shell-bar-normal.png", "rect": [0, 0, 400, 136], "cell_background": "#808080",
            "measurements": {"height": height},
            "deviations": [{"key": "height", "expected": 36, "measured": height, "ok": ok}]}


class TestReportShell(unittest.TestCase):
    # Reference captions in several scripts: the page must round-trip them as UTF-8, whatever the host locale.
    CAPTIONS = ["5 states of icon button", "アイコンボタンの5つの状態", "حالات زر الأيقونة الخمس"]

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.ref = self.d / "ref"
        (self.ref / "icon-buttons").mkdir(parents=True)
        for i, caption in enumerate(self.CAPTIONS, 1):
            png(self.ref / "icon-buttons" / f"0{i}-states.png", (0.2, 0.3, 0.8))
        (self.ref / "icon-buttons" / "index.tsv").write_text(
            "".join(f"0{i}-states.png\t{c}\n" for i, c in enumerate(self.CAPTIONS, 1)), encoding="utf-8")
        for mode, color, ok, h in (("dark", (0.1, 0.1, 0.1), True, 36.0), ("light", (0.9, 0.9, 0.9), False, 30.0)):
            (self.d / mode).mkdir()
            png(self.d / mode / "shell-bar-normal.png", color)
            (self.d / mode / "measurements.json").write_text(json.dumps([measurement(ok, h)]), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_bar_section(self):
        out = report_shell.generate(self.d, self.ref)
        self.assertEqual(out, self.d / "report.html")
        page = out.read_text(encoding="utf-8")
        self.assertIn('<section id="bar">', page)
        self.assertIn("ref/icon-buttons/01-states.png", page)        # reference of the surface
        self.assertIn(self.CAPTIONS[0], page)
        for mode in ("dark", "light"):
            thumb = self.d / "thumbnails" / f"{mode}-bar-normal.png"
            self.assertTrue(thumb.exists(), thumb)
            self.assertIn(f"thumbnails/{mode}-bar-normal.png", page)
        self.assertIn("witness-bar", page)
        # Deviations of both modes: conforming in dark, deviation in light.
        self.assertIn("deviation ok", page)
        self.assertIn("deviation ko", page)
        self.assertLess(page.index("Dark"), page.index("Light"))

    def test_summary_per_mode(self):
        page = report_shell.generate(self.d, self.ref).read_text(encoding="utf-8")
        self.assertRegex(page, r"<tr><th>Dark</th><td>1</td><td>0</td></tr>")
        self.assertRegex(page, r"<tr><th>Light</th><td>0</td><td>1</td></tr>")

    def test_non_latin_captions_round_trip(self):
        # Several references of one component: the extra views are listed as links with their (non-Latin) captions.
        page = report_shell.generate(self.d, self.ref).read_text(encoding="utf-8")
        for caption in self.CAPTIONS:
            self.assertIn(caption, page)

    def test_component_of_each_surface(self):
        for surface in set(expected.SURFACE.values()):
            self.assertIn(surface, report_shell.COMPONENT)

    def test_a_mode_missing(self):
        shutil.rmtree(self.d / "light")
        self.assertEqual(report_shell.main([str(self.d)]), 1)
        self.assertFalse((self.d / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
