import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import summary


class TestSummary(unittest.TestCase):
    def test_gtk4(self):
        t = ("(python3:1): Gtk-WARNING **: 22:45:05.232: GtkGizmo 0x2a3c6820 (trough) reported min width -2, but sizes must be >= 0\n"
             "Gtk[2]: WARNING: AdwGizmo 0x55 (tabboxchild) reported min width -4, but sizes must be >= 0\n")
        neg, addresses, errors = summary.analyze_journal(t)
        self.assertEqual(neg[("GtkGizmo", "trough", "width")], 1)
        self.assertEqual(neg[("AdwGizmo", "tabboxchild", "width")], 1)
        self.assertEqual(addresses, ["0x2a3c6820", "0x55"])
        self.assertEqual(errors, [])

    def test_gtk3_and_css(self):
        t = ("Gtk-WARNING **: Negative content width -3 (allocation 1, extents 2x2) while allocating gadget (node slider, owner GtkScrollbar)\n"
             "Gtk-WARNING **: Theme parsing error: gtk.css:12:3: bad\n")
        neg, _, errors = summary.analyze_journal(t)
        self.assertEqual(neg[("gtk3", "slider", "allocation")], 1)
        self.assertEqual(len(errors), 1)

    def test_clean(self):
        neg, _addresses, _errors = summary.analyze_journal("nothing\nGtkBox 0x1 unexpectedly doesn't fit into width of 18\n")
        self.assertEqual(sum(neg.values()), 0)

    def test_text_in_any_script_does_not_hide_a_warning(self):
        # Journals carry application text in the language of the session: the analysis must not depend on it.
        for text in ("設定とファイル", "الإعدادات", "Réglages"):
            t = f"{text}\nGtkGizmo 0x1 (slider) reported min height -1, but sizes must be >= 0\n{text}\n"
            neg, _addresses, _errors = summary.analyze_journal(t)
            self.assertEqual(sum(neg.values()), 1, text)

    def test_expectations(self):
        with tempfile.TemporaryDirectory() as d:
            mode = Path(d) / "dark"
            mode.mkdir()
            (mode / "journal-client4.log").write_text("nothing\n")
            (mode / "journal-settings.log").write_text("nothing\n")
            checks = [{"name": "handle", "expected": [24, 24], "measured": [24, 24], "ok": True}]
            (mode / "client4-data.json").write_text(json.dumps({"checks": checks}))
            self.assertEqual(summary.main(d), 0)
            checks.append({"name": "back", "expected": 32, "measured": 30, "ok": False})
            (mode / "client4-data.json").write_text(json.dumps({"checks": checks}))
            self.assertEqual(summary.main(d), 1)
            data = json.loads((Path(d) / "summary.json").read_text())
            self.assertEqual(len(data["dark/client4"]["unmet_expectations"]), 1)
            self.assertEqual(data["dark/settings"]["unmet_expectations"], [])


if __name__ == "__main__":
    unittest.main()
