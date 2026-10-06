import json, sys, unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import grid  # noqa: E402

TOKENS = json.loads((ICI.parent / "reference" / "m3e-tokens.json").read_text(encoding="utf-8"))
# Colour roles known to the repository: every role a token points to, plus the roles cited directly by the rows.
ROLES = {t["value"] for comp in TOKENS.values() for t in comp.values() if t["type"] == "role"}
ROLES |= {"surface", "primary", "error", "on_error"}


class TestGrid(unittest.TestCase):
    def test_unique_ids(self):
        ids = [r.id for r in grid.ROWS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_known_states(self):
        for r in grid.ROWS:
            self.assertLessEqual(set(r.expected), set(r.states), r.id)
            self.assertLessEqual(set(r.states), set(grid.STATES), r.id)

    def test_overlays_single_state(self):
        for i in ("menu", "tooltip", "dialog"):
            self.assertEqual(next(r for r in grid.ROWS if r.id == i).states, ["normal"])

    def test_every_reference_exists(self):
        for r in grid.ROWS:
            for ref in grid.references(r):
                if ref.startswith("@"):
                    self.assertIn(ref[1:], ROLES, f"{r.id}: role {ref}")
                else:
                    comp, key = ref.split(".")
                    self.assertIn(key, TOKENS.get(comp, {}), f"{r.id}: token {ref}")

    def test_adw_rows_only_in_adw(self):
        ids3 = {r.id for r in grid.rows_for("gtk3")}
        ids4 = {r.id for r in grid.rows_for("gtk4")}
        for i in ("adw-entry-row", "adw-split"):
            self.assertNotIn(i, ids3); self.assertNotIn(i, ids4)
            self.assertIn(i, {r.id for r in grid.rows_for("adw")})

    def test_header_witness(self):
        e = next(r for r in grid.ROWS if r.id == "header")
        self.assertEqual(e.expected["hover"]["height"], 29)
        self.assertEqual(e.expected["hover"]["width"], 29)

    def test_batch(self):
        self.assertTrue(all(1 <= r.batch <= 8 for r in grid.ROWS))
        self.assertEqual({r.id for r in grid.rows_for("gtk4", batch=3)}, {"switch", "checkbox", "radio", "header"})  # witness always included


if __name__ == "__main__":
    unittest.main()
