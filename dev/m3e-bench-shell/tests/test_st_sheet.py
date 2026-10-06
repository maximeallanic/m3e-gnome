"""st_sheet.py: declarations St would ignore without a word."""
import contextlib, io, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import st_sheet  # noqa: E402


class TestStSheet(unittest.TestCase):
    def test_broken_sheet(self):
        e = st_sheet.errors(".m3e-test { colour: red; }\n.m3e-test { width: 12qq; }\n")
        self.assertEqual(e, ["1: property unknown to St: colour", "2: unit unknown to St: width: 12qq"])

    def test_valid_sheet(self):
        css = """/* comment { colour: red; } */
#panel { background-color: rgba(24, 18, 11, 0.55); height: 36px; font-size: 1.1em;
  transition-duration: 150ms; border-radius: 99px; color: #e3e2e9; }
.popup-menu { -arrow-border-radius: 16px; margin: 0 4pt; background-image: url("assets/a2b.svg");
  font-feature-settings: "tnum"; box-shadow: 0 1px 3px rgba(0,0,0,.3); }
* { font-weight: normal !important; }
"""
        self.assertEqual(st_sheet.errors(css), [])

    def test_status_bar_extension_properties(self):
        # Read by the status-bar extension (battery.js): known, so the theme's own sheet stays clean.
        self.assertEqual(st_sheet.errors("#panel .status-bar-battery { -status-bar-height: 16px; "
                                         "-status-bar-low: #ba1a1a; }"), [])

    def test_unknown_function(self):
        # St writes "Ignoring length property that isn't a number" for calc().
        self.assertEqual(st_sheet.errors("#panel { width: calc(100% - 60px); color: st-mix(#fff, #000, 50%); }"),
                         ["1: function unknown to St: width: calc()"])

    def test_percentage(self):
        # shell.log: "percentage lengths not currently supported"; valid inside a function.
        self.assertEqual(st_sheet.errors("a { width: 50%; color: st-mix(#fff, st-mix(#000, #111, 9%), 60%); }"),
                         ["1: length percentage not supported by St: width: 50%"])

    def test_side_border_shorthand(self):
        # Observed in the bench: St does not draw "border-bottom: 1px solid c" (per-side shorthand), with no message.
        # Drawn form: border-<side>-width + border-<side>-color (or border: 0 solid c).
        css = ("a { border-bottom: 1px solid #fff; }\nb { border-top: 2px solid red; border-left: 0; }\n"
               "c { border-right: 1px; }\n")
        self.assertEqual(st_sheet.errors(css), [
            "1: per-side border shorthand ignored by St: border-bottom (use border-bottom-width and "
            "border-bottom-color)",
            "2: per-side border shorthand ignored by St: border-top (use border-top-width and border-top-color)",
            "2: per-side border shorthand ignored by St: border-left (use border-left-width and border-left-color)",
            "3: per-side border shorthand ignored by St: border-right (use border-right-width and "
            "border-right-color)"])
        self.assertEqual(st_sheet.errors("a { border: 0 solid #fff; border-bottom-width: 1px; "
                                         "border-bottom-color: #fff; }"), [])

    def test_line_numbers(self):
        e = st_sheet.errors("a {\n  color: red;\n  /* x\n y */\n  border-colour: 0;\n}\n")
        self.assertEqual(e, ["5: property unknown to St: border-colour"])

    def test_non_latin_text_is_not_mangled(self):
        # Comments, font names and font features in several scripts: no false positive, line numbers kept, and a real
        # error after a multi-line comment in CJK / Arabic is still reported on the right line.
        css = ("/* 日本語のコメント { colour: red; } */\n"
               ".a { font-family: \"Noto Sans CJK JP\", \"思源黑体\", \"Amiri\", \"Noto Naskh Arabic\"; color: red; }\n"
               "/* تعليق\n متعدد الأسطر */\n"
               ".b { colour: red; font-feature-settings: \"tnum\"; }\n"
               ".c { width: 12qq; }\n")
        self.assertEqual(st_sheet.errors(css), ["5: property unknown to St: colour",
                                                "6: unit unknown to St: width: 12qq"])

    def test_stock_sheets_are_clean(self):
        sheets = sorted(st_sheet.STOCK.glob("gnome-shell-*.css"))
        self.assertTrue(sheets)
        for f in sheets:
            self.assertEqual(st_sheet.errors(f.read_text(encoding="utf-8")), [], f)

    def test_main(self):
        with tempfile.NamedTemporaryFile("w", suffix=".css", encoding="utf-8") as f:
            f.write(".x { colour: red; }\n")
            f.flush()
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(st_sheet.main([f.name]), 1)
            self.assertIn(f"{f.name}:1: property unknown to St: colour", out.getvalue())
        self.assertEqual(st_sheet.main(sorted(map(str, st_sheet.STOCK.glob("*.css")))), 0)


if __name__ == "__main__":
    unittest.main()
