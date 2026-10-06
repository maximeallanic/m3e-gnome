import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import verify_sheet as vs  # noqa: E402

TOKENS = json.loads(vs.DEFAULT_TOKENS.read_text(encoding="utf-8"))


class SheetTest(unittest.TestCase):
    # Known theme defects (reported to the theme owner): m3e-extensions-template.css:28 repeats the 16 px token value
    # without naming it three times, and :189 still uses the French token suffix `.taille` (now `.size`). Remove this
    # decorator once the template is fixed (an unexpected success then reports it).
    @unittest.expectedFailure
    def test_repository_template_conforms(self):
        self.assertEqual(vs.token_errors(vs.DEFAULT_SHEET.read_text(encoding="utf-8"), TOKENS), [])

    def test_important_is_allowed(self):
        css = ".a {\n  padding: 8px !important; /* SmallIconButton.DefaultLeadingSpace */\n}\n"
        self.assertEqual(vs.token_errors(css, TOKENS), [])

    def test_bold_is_refused(self):
        self.assertTrue(vs.token_errors(".a {\n  font-weight: bold !important;\n}\n", TOKENS))

    def test_hardcoded_colour_is_refused(self):
        self.assertTrue(vs.token_errors(".a {\n  color: #ff0000 !important;\n}\n", TOKENS))

    def test_wrong_token_value_is_refused(self):
        css = ".a {\n  padding: 9px !important; /* SmallIconButton.DefaultLeadingSpace */\n}\n"
        self.assertTrue(vs.token_errors(css, TOKENS))

    def test_extension_properties_are_known_to_the_st_check(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "s.css"
            f.write_text(".a {\n  -x-offset: 4px;\n  -progress-bar-background: #fff;\n}\n", encoding="utf-8")
            self.assertEqual(vs.st_errors(f), [])
            f.write_text(".a {\n  colour: red;\n}\n", encoding="utf-8")
            self.assertTrue(vs.st_errors(f))


if __name__ == "__main__":
    unittest.main()
