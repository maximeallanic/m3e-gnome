"""palettes.py: the SystemUI roles appended to the rendered colour sheet, and the real render (needs matugen)."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH_SHELL = HERE.parent
BENCH = BENCH_SHELL.parent / "m3e-bench"
sys.path.insert(0, str(BENCH_SHELL))
sys.path.insert(0, str(BENCH))
import palettes  # noqa: E402
from colors import read_colors  # noqa: E402

PALETTE = {"colors": {
    "primary": {"default": {"hex": "#112233", "opacity": "1.0"}},
    "on_primary": {"default": {"hex": "#fefefe", "opacity": "1.0"}},
    "on_surface": {"default": {"hex": "#0a0b0c", "opacity": "1.0"}},
    "surface_effect_1": {"default": {"hex": "#fff8f4", "opacity": "0.54"}},
    "surface_effect_0": {"default": {"hex": "#ffddb3", "opacity": "0.5"}},
    "surface_effect_12": {"default": {"hex": "#010203", "opacity": "0.2"}},
    "surface_effects": {"default": {"hex": "#ffffff", "opacity": "1.0"}},
}}


class TestEffectRoles(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)

    def test_effect_lines_only_surface_effect_roles(self):
        lines = palettes.effect_lines(PALETTE)
        self.assertEqual(lines, "  --surface_effect_0: #ffddb3;\n  --surface_effect_0-opacity: 0.5;\n"
                                "  --surface_effect_1: #fff8f4;\n  --surface_effect_1-opacity: 0.54;\n"
                                "  --surface_effect_12: #010203;\n  --surface_effect_12-opacity: 0.2;\n")

    def test_write_colors_readable_by_measure(self):
        (self.d / "palette.json").write_text(json.dumps(PALETTE), encoding="utf-8")
        (self.d / "colors-gtk4.css").write_text(":root {\n  --primary: #112233;\n}\n", encoding="utf-8")
        colors = read_colors(palettes.write_colors(self.d))
        self.assertEqual(colors["primary"], (0x11, 0x22, 0x33))
        self.assertEqual(colors["surface_effect_1"], (255, 248, 244))
        self.assertEqual(colors["opacity.surface_effect_1"], 0.54)
        self.assertNotIn("surface_effects", colors)

    def test_overview_ink_follows_the_mode(self):
        # The dark overview is a surface (on_surface), the light one is primary (on_primary).
        self.assertEqual(palettes.overview_lines(PALETTE, "dark"), "  --overview_ink: #0a0b0c;\n")
        self.assertEqual(palettes.overview_lines(PALETTE, "light"), "  --overview_ink: #fefefe;\n")
        for mode, ink in (("dark", (10, 11, 12)), ("light", (254, 254, 254))):
            d = self.d / mode
            d.mkdir()
            (d / "palette.json").write_text(json.dumps(PALETTE), encoding="utf-8")
            (d / "colors-gtk4.css").write_text(":root {}\n", encoding="utf-8")
            self.assertEqual(read_colors(palettes.write_colors(d))["overview_ink"], ink)

    def test_palette_without_effect_roles_refused(self):
        (self.d / "palette.json").write_text(json.dumps({"colors": {"primary": PALETTE["colors"]["primary"]}}),
                                             encoding="utf-8")
        (self.d / "colors-gtk4.css").write_text(":root {}\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            palettes.write_colors(self.d)
        self.assertFalse((self.d / "colors.css").exists())


class TestRealRender(unittest.TestCase):
    """Renders the real theme (matugen) into a temporary directory; skipped without the base theme or the tools."""

    def test_render_both_modes(self):
        import os
        base = Path(os.environ.get("M3E_BASE_THEME") or Path.home() / ".themes" / "Material-Gnome")
        if not base.is_dir() or not shutil.which("matugen"):
            self.skipTest("base theme or matugen not available")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out)
        palettes.render_all(out, base_theme=base)
        for mode in palettes.MODES:
            colors = read_colors(out / mode / "colors.css")
            self.assertIn("surface_effect_1", colors)
            self.assertIn("opacity.surface_effect_1", colors)
            self.assertTrue((out / mode / "gnome-shell.css").stat().st_size > 0)
        self.assertNotEqual(read_colors(out / "dark" / "colors.css")["surface"],
                            read_colors(out / "light" / "colors.css")["surface"])


if __name__ == "__main__":
    unittest.main()
