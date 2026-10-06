"""Headless-safe tests of the bench: isolation guard and paging logic. Nothing here opens a window: bench.py itself
only runs inside the nested Shell (see its docstring), so it is only ever launched here to check that it REFUSES."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import grid  # noqa: E402
import isolation  # noqa: E402
import paging  # noqa: E402

NESTED = {"WAYLAND_DISPLAY": "m3e-bench-4242", "GDK_BACKEND": "wayland"}


class TestIsolation(unittest.TestCase):
    def test_nested_socket_accepted(self):
        self.assertIsNone(isolation.check_isolated(NESTED))

    def test_real_sockets_refused(self):
        for display in ("", "wayland-0", "wayland-1", "m3e-bench-", "m3e-bench-12x", "x-m3e-bench-12"):
            self.assertIsNotNone(isolation.check_isolated({"WAYLAND_DISPLAY": display}), display)

    def test_x11_fallback_refused(self):
        self.assertIsNotNone(isolation.check_isolated({**NESTED, "DISPLAY": ":0"}))
        self.assertIsNotNone(isolation.check_isolated({**NESTED, "GDK_BACKEND": "x11"}))

    def test_bench_script_refuses_outside_nested_shell(self):
        # The guard runs before anything touches GTK: no window can open, whatever the environment says.
        with tempfile.TemporaryDirectory() as out:
            for display in (None, "wayland-0"):
                env = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"}
                if display:
                    env["WAYLAND_DISPLAY"] = display
                r = subprocess.run([sys.executable, str(ICI / "bench.py"), "--toolkit", "gtk4", "--batch", "2",
                                    "--out", out], env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("refused", r.stderr)
                self.assertEqual(list(Path(out).iterdir()), [])


class TestPaging(unittest.TestCase):
    def test_page_name(self):
        self.assertEqual(paging.page_name("gtk4", 2, 0), "gtk4-b2-p0")

    def test_every_cell_is_placed_by_some_page(self):
        # Headless version of "all rows of a batch are placed": follow `deferred` ids the way the paging does.
        for tk in sorted(grid.TOOLKITS):
            for batch in range(2, 9):
                expected = {(r.id, s) for r in grid.rows_for(tk, batch) for s in r.states}
                placed, wanted, pages = set(), None, 0
                while pages < 20:
                    rows, deferred = paging.select_rows(tk, batch, wanted)
                    placed |= {(r.id, s) for r in rows for s in r.states}
                    if not deferred:
                        break
                    wanted, pages = deferred, pages + 1
                self.assertEqual(placed, expected, (tk, batch))

    def test_dialog_alone_on_its_page(self):
        rows, deferred = paging.select_rows("gtk3", 6)
        self.assertNotIn("dialog", [r.id for r in rows])
        self.assertEqual(deferred, ["dialog"])
        rows, deferred = paging.select_rows("gtk3", 6, ["dialog"])
        self.assertEqual([r.id for r in rows], ["dialog"])
        self.assertEqual(deferred, [])

    def test_wanted_keeps_the_witness(self):
        rows, _ = paging.select_rows("gtk4", 2, ["button"])
        self.assertEqual([r.id for r in rows], ["header", "button"])

    def test_fit_rows(self):
        bounds = [("header", 16, 40), ("a", 70, 100), ("b", 190, 100), ("c", 300, 20), ("d", 330, 30)]
        # window of 360: c ends at 320 and fits (< 352), d ends at 360 and does not.
        self.assertEqual(paging.fit_rows(bounds, 360), ["d"])
        # once a row overflows, every following row is deferred, even a small one that would fit
        self.assertEqual(paging.fit_rows(bounds, 280), ["b", "c", "d"])
        self.assertEqual(paging.fit_rows(bounds, 1000), [])

    def test_cell_record_margin(self):
        c = paging.cell_record("button", "hover", (100, 50, 80, 40), (1000, 800))
        self.assertEqual(c, {"row": "button", "state": "hover", "x": 88, "y": 38, "w": 104, "h": 64})

    def test_overlay_zones(self):
        menu = paging.cell_record("menu", "normal", (100, 50, 80, 40), (1000, 800))
        self.assertEqual((menu["x"], menu["y"], menu["w"], menu["h"]), (40, 90, 380, 300))
        dialog = paging.cell_record("dialog", "normal", (0, 0, 1, 1), (1000, 800))
        self.assertEqual((dialog["x"], dialog["y"], dialog["w"], dialog["h"]), (170, 180, 660, 440))

    def test_layout_document_keys(self):
        d = paging.layout_document("gtk4", 2, 0, (1000, 800), "Virtual-1", (1000, 800), ["x"], [])
        self.assertEqual(set(d), {"toolkit", "batch", "page", "window", "screen", "logical_screen", "ignored_inputs",
                                  "remaining", "cells"})
        self.assertTrue(d["ignored_inputs"])


if __name__ == "__main__":
    unittest.main()
