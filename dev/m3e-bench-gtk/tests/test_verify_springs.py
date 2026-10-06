import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import verify_springs as v

THEME = HERE.parents[1] / "theme"
MOTION = THEME / "motion" / "gtk"
TABLE = v.table3((MOTION / "m3e-gtk3-motion.css").read_text())
NAMES = {n for n, _ in v.VAR4.findall((MOTION / "m3e-gtk4-motion.css").read_text())}
E = "159ms cubic-bezier(0.2295, 0.1781, 0.2051, 0.9454)"


class TestVerifySprings(unittest.TestCase):
    def test_tables(self):
        self.assertEqual(len(TABLE), 6)
        self.assertIn("fast-spatial", NAMES)

    def test_gtk3_conformant(self):
        self.assertEqual(v.verify3(f"a {{ transition: color {E}; /* M3E-visual: M3E.Spring.DefaultEffects */ }}", TABLE), [])

    def test_gtk3_curve_outside_base(self):
        self.assertTrue(v.verify3("a { transition: color 150ms cubic-bezier(0.2, 0, 0, 1); /* x */ }", TABLE))

    def test_gtk3_missing_comment(self):
        self.assertTrue(v.verify3(f"a {{ transition: color {E}; /* M3E-visual: spring */ }}", TABLE))

    def test_gtk3_keyword(self):
        self.assertTrue(v.verify3(f"a {{ transition: color {E}, opacity 0.2s ease; /* M3E.Spring.DefaultEffects */ }}", TABLE))

    def test_gtk4(self):
        ok = "a { transition: color var(--m3e-spring-default-effects-duration) var(--m3e-spring-default-effects-curve); }"
        self.assertEqual(v.verify4(ok, NAMES), [])
        self.assertTrue(v.verify4("a { transition: color 200ms linear; }", NAMES))
        self.assertTrue(v.verify4("a { transition: color var(--m3e-spring-fast-spatial-duration) "
                                  "var(--m3e-spring-default-effects-curve); }", NAMES))
        self.assertEqual(v.verify4("a { animation: none; transition: none; }", NAMES), [])

    def test_follows_imports(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "index.css").write_text('@import url("part.css");\n/* @import url("commented.css"); */\n')
            (root / "part.css").write_text("a { color: red; }\n")
            self.assertEqual([p.name for p in v.parts(root / "index.css")], ["index.css", "part.css"])

    def test_real_theme(self):
        self.assertEqual(v.main(MOTION, THEME / "overrides" / "m3e-gtk3.css", THEME / "overrides" / "m3e-gtk4.css"), 0)


if __name__ == "__main__":
    unittest.main()
