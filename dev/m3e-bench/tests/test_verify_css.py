import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import verify_css  # noqa: E402


def sheet(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".css", delete=False)
    f.write(text)
    f.close()
    return f.name


class TestVerifyCss(unittest.TestCase):
    def test_gtk3_transform_refused(self):
        e = verify_css.verify(sheet("check {\n  transform: none;\n}\n"), "3.0")
        self.assertEqual(len(e), 1)
        self.assertIn("2:", e[0])

    def test_gtk4_transform_accepted(self):
        self.assertEqual(verify_css.verify(sheet("check {\n  transform: none;\n}\n"), "4.0"), [])

    def test_unknown_colour_ignored(self):
        # @colours are only resolved with the theme: not a syntax error
        self.assertEqual(verify_css.verify(sheet("button { color: @primary; }\n"), "3.0"), [])

    def test_imported_part_is_parsed_next_to_the_index(self):
        # An index file @imports its parts by relative url: they must be resolved and checked too.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "part.css").write_text("check {\n  transform: none;\n}\n")
            (Path(d) / "index.css").write_text('@import url("part.css");\n')
            e = verify_css.verify(Path(d) / "index.css", "3.0")
            self.assertEqual(len(e), 1)
            self.assertIn("part.css:2:", e[0])


if __name__ == "__main__":
    unittest.main()
