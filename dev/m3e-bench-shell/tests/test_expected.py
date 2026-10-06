"""Table of expected rows of the Shell bench: toolkit, token and role references, ids, surfaces."""
import json, re, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH_SHELL = HERE.parent
BENCH = BENCH_SHELL.parent / "m3e-bench"
sys.path.insert(0, str(BENCH_SHELL))
sys.path.insert(0, str(BENCH))
import expected  # noqa: E402
import grid  # noqa: E402

TOKENS = json.loads((BENCH_SHELL.parent / "reference" / "m3e-tokens.json").read_text(encoding="utf-8"))
# Fixed copy of a rendered colour sheet (dark): list of known roles.
ROLES = set(re.findall(r"--([a-z_]+)\s*:", (HERE / "data" / "colors.css").read_text(encoding="utf-8")))
# SystemUI roles appended to the bench's colors.css by palettes.py (palette.json, docs/design-notes.md).
ROLES |= {f"surface_effect_{i}" for i in range(4)}
ROLES.add("overview_ink")   # content colour on the overview background, depends on the mode (palettes.overview_lines)
EXTENSION = BENCH_SHELL / "m3e-bench-style@maximeallanic.github.io"
MODULES = sorted((BENCH_SHELL / "expected").glob("*.py"))
# Names private to the repository's owner (assembled so that this guard does not match its own source).
PRIVATE = re.compile("|".join(["ha" + "qs", "mai" + "son", "google" + "-hub", "han" + "abi", Path.home().name, "/home/"]),
                     re.I)


class TestExpected(unittest.TestCase):
    def test_rows_not_empty(self):
        self.assertTrue(expected.ROWS)
        for row in expected.ROWS:
            self.assertIsInstance(row, grid.Row)

    def test_toolkit_shell(self):
        for row in expected.ROWS:
            self.assertEqual(row.toolkits, {"shell"}, row.id)

    def test_token_references(self):
        for row in expected.ROWS:
            for ref in grid.references(row):
                if ref.startswith("@"):
                    continue
                component, _, key = ref.partition(".")
                self.assertIn(component, TOKENS, f"{row.id}: {ref}")
                self.assertIn(key, TOKENS[component], f"{row.id}: {ref}")

    def test_token_value_keys_are_english(self):
        # The converted token schema: every token has "type" and "value" (or the typography keys), never French names.
        for component, tokens in TOKENS.items():
            for key, token in tokens.items():
                if isinstance(token, dict):
                    self.assertFalse({"valeur", "taille", "interligne", "approche"} & set(token), f"{component}.{key}")

    def test_roles(self):
        self.assertIn("surface", ROLES)
        for row in expected.ROWS:
            for ref in grid.references(row):
                if ref.startswith("@"):
                    # "@dark.role": role of the dark palette (lock screen, GDM; measure.colors_for).
                    self.assertIn(ref[1:].removeprefix("dark."), ROLES, f"{row.id}: {ref}")

    def test_unique_ids(self):
        ids = [row.id for row in expected.ROWS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_known_states(self):
        for row in expected.ROWS:
            self.assertLessEqual(set(row.expected), set(grid.STATES), row.id)
            self.assertLessEqual(set(row.states), set(grid.STATES), row.id)

    def test_known_metric_keys(self):
        allowed = {"height", "width", "radius", "stroke", "background", "text", "layer", "dominant"}
        for row in expected.ROWS:
            for state, metrics in row.expected.items():
                self.assertLessEqual(set(metrics), allowed, f"{row.id}/{state}")

    def test_witness_bar(self):
        row = {r.id: r for r in expected.ROWS}["witness-bar"]
        self.assertEqual(row.batch, 2)
        self.assertEqual(row.expected, {"normal": {"height": 36}})

    def test_surface_of_each_row(self):
        for row in expected.ROWS:
            self.assertIn(row.id, expected.SURFACE, row.id)
        self.assertEqual(expected.SURFACE["witness-bar"], "bar")
        self.assertEqual(set(expected.SURFACE), {row.id for row in expected.ROWS})

    def test_surfaces_for_batch(self):
        # Batch 2: the bar (witness); another batch keeps the witnesses; without a batch: all, in row order.
        self.assertEqual(expected.surfaces_for(2), ["bar"])
        self.assertIn("bar", expected.surfaces_for(7))
        in_row_order = []
        for row in expected.ROWS:
            if expected.SURFACE[row.id] not in in_row_order:
                in_row_order.append(expected.SURFACE[row.id])
        self.assertEqual(expected.surfaces_for(None), in_row_order)

    def _surfaces_js(self):
        files = sorted((EXTENSION / "surfaces").glob("*.js"))
        self.assertTrue(files, "no surfaces/*.js in the bench extension")
        return {f.name: f.read_text(encoding="utf-8") for f in files}

    def test_surface_defined_in_surfaces_js(self):
        # Every surface cited by expected/ is defined in surfaces/*.js (otherwise Run would fail).
        names = set()
        for source in self._surfaces_js().values():
            names |= set(re.findall(r"^    '?([A-Za-z0-9_-]+)'?: \{", source, re.M))
        self.assertLessEqual(set(expected.SURFACE.values()), names)

    def test_row_ids_agree_with_surfaces_js(self):
        # Contract with the JS side: the cells of the surfaces name expected rows, and every expected row is a cell.
        cited = set()
        for source in self._surfaces_js().values():
            cited |= set(re.findall(r"\brow: '([a-z0-9-]+)'", source))
        self.assertEqual(cited - {r.id for r in expected.ROWS}, set(), "cells of surfaces/*.js without an expected row")
        self.assertEqual({r.id for r in expected.ROWS} - cited, set(), "expected rows without a cell in surfaces/*.js")

    def test_gdm_surfaces(self):
        # Surfaces of the login screen (nested Shell in gdm mode): known to SURFACE and to surfaces.js.
        self.assertTrue(expected.SURFACES_GDM)
        self.assertLessEqual(expected.SURFACES_GDM, set(expected.SURFACE.values()))
        self.assertNotIn("bar", expected.SURFACES_GDM)

    def test_no_file_over_500_lines(self):
        for module in MODULES:
            self.assertLessEqual(len(module.read_text(encoding="utf-8").splitlines()), 500, module.name)

    def test_nothing_personal_or_third_party(self):
        # The theme has no rules for the owner's private extensions: no row, surface or comment mentions them.
        for module in MODULES:
            self.assertIsNone(PRIVATE.search(module.read_text(encoding="utf-8")), module.name)
        self.assertNotIn("extensions", set(expected.SURFACE.values()))


class TestCommandLine(unittest.TestCase):
    def _run(self, *args):
        import subprocess
        return subprocess.run([sys.executable, "-m", "expected", *args], cwd=BENCH_SHELL, capture_output=True,
                              text=True, timeout=60)

    def test_all_surfaces(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().split(","), expected.surfaces_for(None))

    def test_batch(self):
        self.assertEqual(self._run("2").stdout.strip(), "bar")

    def test_gdm(self):
        self.assertEqual(self._run("--gdm").stdout.strip().split(","), sorted(expected.SURFACES_GDM))


if __name__ == "__main__":
    unittest.main()
