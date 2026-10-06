import json, re, sys, tempfile, unittest
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import report  # noqa: E402


def png(path, w=400, h=200):
    pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, w, h)
    pb.fill(0x202020ff)
    pb.savev(str(path), "png", [], [])


def deviation(key, ok):
    return {"key": key, "expected": 40, "measured": 41 if ok else 50, "ok": ok}


class TestReport(unittest.TestCase):
    def test_minimal_report(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as ref:
            d, ref = Path(d), Path(ref)
            for tk in ("gtk3", "gtk4", "adw"):
                png(d / f"{tk}-b2.png")
            (ref / "buttons").mkdir()
            png(ref / "buttons" / "01-diagram.png")
            png(ref / "buttons" / "02-tonal-button-states.png")
            (ref / "buttons" / "index.tsv").write_text("01-diagram.png\tDiagram.\n02-tonal-button-states.png\tTonal button states.\n")
            measurements = [{"toolkit": tk, "batch": 2, "row": "button", "state": e, "rect": [10, 10 + 30 * i, 80, 30], "image": f"{tk}-b2.png",
                        "deviations": [deviation("height", tk != "gtk3")]}
                       for tk in ("gtk3", "gtk4", "adw") for i, e in enumerate(("normal", "hover"))]
            (d / "measurements.json").write_text(json.dumps(measurements))
            page = report.generate(d, ref).read_text()
            section = page[page.index('id="buttons"'):]
            section = section[:section.index("</section>")]
            self.assertEqual(len(re.findall(r"<img ", section)), 4)          # reference + 3 toolkits
            self.assertIn("02-tonal-button-states.png", section)              # the "states" view is preferred
            self.assertEqual(len(re.findall(r'class="deviation (ok|ko)"', section)), 6)
            self.assertEqual(len(re.findall(r'class="deviation ko"', section)), 2)
            for tk in ("gtk3", "gtk4", "adw"):
                self.assertTrue((d / "thumbnails" / f"{tk}-button.png").exists())

    def test_unknown_component_has_no_reference(self):
        self.assertEqual(report.COMPONENT["header"], None)


if __name__ == "__main__":
    unittest.main()
