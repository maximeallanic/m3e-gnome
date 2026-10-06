import math, sys, tempfile, unittest
from pathlib import Path

import cairo

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import measure  # noqa: E402

BACKGROUND = (0x1a, 0x1b, 0x21)


def hexa(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def image(draw, l=200, h=100):
    """Draws with cairo on the BACKGROUND colour, returns a GdkPixbuf."""
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, l, h)
    c = cairo.Context(s)
    c.set_source_rgb(*(x / 255 for x in BACKGROUND))
    c.paint()
    draw(c)
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        s.write_to_png(f.name)
        return measure.load(f.name)


def rounded_rect(c, x, y, l, h, r):
    c.new_sub_path()
    c.arc(x + l - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + l - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    c.close_path()


def fill(color, x, y, l, h, r):
    def d(c):
        rounded_rect(c, x, y, l, h, r)
        c.set_source_rgb(*(v / 255 for v in hexa(color)))
        c.fill()
    return d


TOKENS = {
    "ButtonSmall": {"ContainerHeight": {"type": "dp", "value": 40.0},
                    "ContainerShapeRound": {"type": "shape", "value": "full"}},
    "FilledTextField": {"ContainerShape": {"type": "corners", "value": [4.0, 4.0, 0.0, 0.0]}},
    "FilledTonalButton": {"ContainerColor": {"type": "role", "value": "secondary_container"},
                          "LabelTextColor": {"type": "role", "value": "on_secondary_container"}},
    "State": {"HoverStateLayerOpacity": {"type": "opacity", "value": 0.08}},
    "SplitButtonMedium": {"ContainerShape": {"type": "shape", "value": "full"},
                          "InnerCornerCornerSize": {"type": "dp", "value": 4.0}},
}
COLORS = {"secondary_container": hexa("#404659"), "on_secondary_container": hexa("#dce2f9"),
            "surface": BACKGROUND}


def M(**kw):
    base = dict(height=0, width=0, radius=[0, 0, 0, 0], stroke=0, background=BACKGROUND, text=BACKGROUND, dominant=BACKGROUND)
    base.update(kw)
    return measure.Measurements(**base)


class TestDeltaE(unittest.TestCase):
    def test_delta_e_identical(self):
        self.assertEqual(measure.delta_e2000((10, 20, 30), (10, 20, 30)), 0)

    def test_delta_e_reference(self):
        # Sharma, Wu, Dalal (2005), paire 1
        self.assertAlmostEqual(measure.delta_e2000_lab((50, 2.6772, -79.7751), (50, 0, -82.7485)), 2.0425, places=4)
        # paire 17
        self.assertAlmostEqual(measure.delta_e2000_lab((50, 2.5, 0), (73, 25, -18)), 27.1492, places=4)


class TestMeasureCell(unittest.TestCase):
    def test_rounded_rect(self):
        pb = image(fill("#404659", 40, 30, 120, 40, 20))
        m = measure.measure_cell(pb, (0, 0, 200, 100), BACKGROUND)
        self.assertAlmostEqual(m.height, 40, delta=1)
        self.assertAlmostEqual(m.width, 120, delta=1)
        for r in m.radius:
            self.assertAlmostEqual(r, 20, delta=1)
        self.assertLess(measure.delta_e2000(m.background, hexa("#404659")), 1)

    def test_low_contrast_container_needs_a_lower_threshold(self):
        # A container 5 levels from its surroundings (Pixel tile in dark mode): invisible at the default threshold
        # (6), measured once the row lowers it.
        tile = tuple(b + 5 for b in BACKGROUND)
        d = fill("#%02x%02x%02x" % tile, 40, 20, 120, 56, 28)
        self.assertEqual(measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND).height, 0)
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND, threshold=2)
        self.assertAlmostEqual(m.height, 56, delta=1)
        self.assertAlmostEqual(m.width, 120, delta=1)
        self.assertEqual(m.background, tile)

    def test_faint_label_needs_a_lower_text_contrast(self):
        # Label 12 levels from its container (30 % opacity): not text at the default contrast (16).
        container = (90, 78, 60)
        label = (86, 66, 48)

        def d(c):
            fill("#%02x%02x%02x" % container, 30, 20, 140, 60, 30)(c)
            c.set_source_rgb(*(v / 255 for v in label))
            c.rectangle(80, 40, 40, 20)
            c.fill()
        self.assertEqual(measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND).text, container)
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND, text_contrast=8)
        self.assertEqual(m.text, label)

    def test_radius_12(self):
        pb = image(fill("#404659", 50, 20, 100, 56, 12))
        m = measure.measure_cell(pb, (0, 0, 200, 100), BACKGROUND)
        for r in m.radius:
            self.assertAlmostEqual(r, 12, delta=1)

    def test_radius_0(self):
        pb = image(lambda c: (c.rectangle(70, 30, 60, 40), c.set_source_rgb(0.25, 0.27, 0.35), c.fill()))
        m = measure.measure_cell(pb, (0, 0, 200, 100), BACKGROUND)
        for r in m.radius:
            self.assertAlmostEqual(r, 0, delta=1)

    def test_stroke(self):
        def d(c):
            rounded_rect(c, 80.5, 30.5, 39, 39, 4)
            c.set_source_rgb(*(v / 255 for v in hexa("#8f9099")))
            c.set_line_width(1)
            c.stroke()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertAlmostEqual(m.stroke, 1, delta=0.5)

    def test_stroke_thick(self):
        def d(c):
            rounded_rect(c, 81.5, 31.5, 37, 37, 3)
            c.set_source_rgb(*(v / 255 for v in hexa("#8f9099")))
            c.set_line_width(3)
            c.stroke()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertAlmostEqual(m.stroke, 3, delta=0.7)

    def test_background_and_text(self):
        def d(c):
            fill("#404659", 40, 30, 120, 40, 20)(c)
            c.rectangle(80, 45, 40, 10)
            c.set_source_rgb(*(v / 255 for v in hexa("#dce2f9")))
            c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(measure.delta_e2000(m.background, hexa("#404659")), 1)
        self.assertLess(measure.delta_e2000(m.text, hexa("#dce2f9")), 1)
        self.assertAlmostEqual(m.height, 40, delta=1)

    def test_no_stroke_on_solid_button(self):
        def d(c):
            fill("#404659", 40, 30, 120, 40, 20)(c)
            c.rectangle(70, 45, 60, 10)
            c.set_source_rgb(*(v / 255 for v in hexa("#dce2f9")))
            c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(m.stroke, 0.5)

    def test_dark_text_on_light(self):
        def d(c):
            fill("#c0c6dd", 40, 30, 120, 40, 12)(c)
            c.rectangle(80, 45, 40, 10)
            c.set_source_rgb(*(v / 255 for v in hexa("#2a3042")))
            c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(measure.delta_e2000(m.text, hexa("#2a3042")), 1)

    def test_antialiased_outline_icon(self):
        # outline with a hole, edges shifted by half a pixel: many grey pixels identical to the edge of the hole
        def d(c):
            c.rectangle(85.3, 35.3, 30, 30)
            c.set_source_rgb(*(v / 255 for v in hexa("#c5c6d0")))
            c.set_line_width(2.5)
            c.stroke()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(measure.delta_e2000(m.text, hexa("#c5c6d0")), 1)

    def test_icon_tiny_holes(self):
        # grid of small empty squares: holes of 1-2 px, no pure background pixel inside
        def d(c):
            for i in range(4):
                c.rectangle(85.4 + 7 * i, 35.4, 5, 28)
            c.set_source_rgb(*(v / 255 for v in hexa("#c5c6d0")))
            c.set_line_width(1.6)
            c.stroke()
            c.rectangle(84, 34, 30, 2); c.fill()
            c.rectangle(84, 63, 30, 2); c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(measure.delta_e2000(m.text, hexa("#c5c6d0")), 1)

    def test_subpixel_text(self):
        # sub-pixel smoothing (GTK 3): each stroke has coloured fringes more numerous than its core
        def d(c):
            fill("#404659", 30, 30, 140, 40, 20)(c)
            for x in range(60, 140, 6):
                for dx, col in ((0, "#597cbb"), (1, "#597cbb"), (2, "#dce2f9"), (3, "#b98a7c"), (4, "#b98a7c")):
                    c.rectangle(x + dx, 40, 1, 20)
                    c.set_source_rgb(*(v / 255 for v in hexa(col)))
                    c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(measure.delta_e2000(m.text, hexa("#dce2f9")), 1)

    def test_dominant(self):
        # active tab: label and indicator of the same colour, no container
        def d(c):
            c.set_source_rgb(*(v / 255 for v in hexa("#b1c5ff")))
            for x in range(80, 120, 8):
                c.rectangle(x, 30, 3, 16)
            c.rectangle(70, 60, 60, 3)
            c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertEqual(m.dominant, hexa("#b1c5ff"))

    def test_no_container(self):
        def d(c):
            for x in range(70, 130, 8):  # "text": spaced vertical strokes
                c.rectangle(x, 40, 3, 16)
            c.set_source_rgb(*(v / 255 for v in hexa("#b1c5ff")))
            c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertEqual(m.background, BACKGROUND)
        self.assertLess(measure.delta_e2000(m.text, hexa("#b1c5ff")), 1)

    def test_ring_alone(self):
        def d(c):
            c.arc(100, 50, 12, 0, 2 * math.pi)
            c.set_source_rgb(*(v / 255 for v in hexa("#c5c6d0")))
            c.set_line_width(3)
            c.stroke()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertLess(measure.delta_e2000(m.text, hexa("#c5c6d0")), 1)
        self.assertAlmostEqual(m.height, 27, delta=1)

    def test_shadow_in_light_mode(self):
        # light mode: container barely darker than the background, shadow darker than the container
        light = hexa("#fbf8ff")

        def d(c):
            c.set_source_rgb(*(v / 255 for v in light))
            c.paint()
            for i, a in enumerate((0.10, 0.18, 0.26)):
                rounded_rect(c, 40 - 3 + i, 30 - 3 + i + 1, 120 + 6 - 2 * i, 40 + 6 - 2 * i, 23 - i)
                c.set_source_rgba(0, 0, 0, a)
                c.fill()
            fill("#e2e0f9", 40, 30, 120, 40, 20)(c)
        m = measure.measure_cell(image(d), (0, 0, 200, 100), light)
        self.assertAlmostEqual(m.height, 40, delta=1)
        for r in m.radius:
            self.assertAlmostEqual(r, 20, delta=1.5)

    def test_real_shadow_light_mode(self):
        # pixels taken from a hovered tonal button in light mode (GTK 4, scale 1.5)
        bg, background = hexa("#fcf8ff"), hexa("#d2d0e9")
        haut = ["#fbf7fe", "#faf6fd", "#f7f3fa", "#f0ecf3", "#e6e2e8"]
        bas = ["#aba8ac", "#bebbc0", "#d5d2d8", "#e6e2e8", "#f0ecf3", "#f7f3fa", "#faf6fd", "#fbf7fe"]

        def d(c):
            c.set_source_rgb(*(v / 255 for v in bg))
            c.paint()
            y = 10
            for col in haut + [None] * 60 + bas:
                c.rectangle(40, y, 120, 1)
                c.set_source_rgb(*(v / 255 for v in (background if col is None else hexa(col))))
                c.fill()
                y += 1
        m = measure.measure_cell(image(d, 200, 100), (0, 0, 200, 100), bg)
        self.assertAlmostEqual(m.height, 60, delta=1)

    def test_real_captures_light_mode(self):
        # crops of real captures (light mode, scale 1.5): the drop shadow must not count
        data = ICI / "tests" / "data"
        bg = hexa("#fcf8ff")
        for name, height in (("light-gtk4-button-hover.png", 60), ("light-gtk3-button-hover.png", 60)):
            pb = measure.load(data / name)
            m = measure.measure_cell(pb, (0, 0, pb.get_width(), pb.get_height()), bg)
            self.assertAlmostEqual(m.height, height, delta=1, msg=name)
        pb = measure.load(data / "light-gtk4-menu-normal.png")
        m = measure.measure_cell(pb, (0, 0, pb.get_width(), pb.get_height()), bg)
        for r in m.radius:
            self.assertAlmostEqual(r, 24, delta=1, msg="menu")

    def test_neighbour_of_other_colour_ignored(self):
        # hover circle + lighter neighbouring glyph (window buttons case)
        def d(c):
            c.arc(100, 50, 20, 0, 2 * math.pi)
            c.set_source_rgb(*(v / 255 for v in hexa("#33343a")))
            c.fill()
            c.rectangle(130, 45, 12, 2)
            c.set_source_rgb(*(v / 255 for v in hexa("#b1c5ff")))
            c.fill()
        m = measure.measure_cell(image(d), (0, 0, 200, 100), BACKGROUND)
        self.assertAlmostEqual(m.height, 40, delta=1)
        self.assertAlmostEqual(m.width, 40, delta=1)


class TestOutsideImage(unittest.TestCase):
    def test_rect_in_image(self):
        pb = image(lambda c: None)
        self.assertTrue(measure.rect_in_image(pb, (10, 10, 50, 50)))
        self.assertFalse(measure.rect_in_image(pb, (180, 10, 50, 50)))
        self.assertFalse(measure.rect_in_image(pb, (-5, 10, 50, 50)))


class TestMain(unittest.TestCase):
    def test_names_by_batch(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            pb = image(fill("#404659", 40, 30, 120, 40, 20))
            pb.savev(str(d / "gtk4-b2.png"), "png", [], [])
            (d / "colors.css").write_text(":root {\n  --secondary_container: #404659;\n  --on_secondary_container: #dce2f9;\n"
                                          "  --surface: #1a1b21;\n}\n")
            (d / "gtk4-b2-screen.json").write_text(json.dumps({"screen": {"scale": 2.0}, "image_scale": 1.0}))
            (d / "layout-gtk4-b2.json").write_text(json.dumps({"toolkit": "gtk4", "batch": 2, "cells": [
                {"row": "button", "state": "normal", "x": 20, "y": 10, "w": 160, "h": 80}]}))
            measure.main(d)
            r = json.loads((d / "measurements.json").read_text())
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0]["image"], "gtk4-b2.png")
            self.assertAlmostEqual(r[0]["measurements"]["height"], 40, delta=1)


class TestFolderPalette(unittest.TestCase):
    def test_colors_css_of_folder(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "colors.css").write_text(":root {\n  --primary: #123456;\n}\n")
            self.assertEqual(measure.colors_for(d)["primary"], (0x12, 0x34, 0x56))

    def test_without_copy_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                measure.colors_for(Path(d))

    def test_dark_palette_of_bench(self):
        # Shell style bench (<out>/<mode>/): the neighbouring dark palette (../dark/colors.css) is read under the
        # prefix "dark." ("@dark.role": lock screen and GDM, always dark), in both modes.
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "dark").mkdir()
            (d / "light").mkdir()
            (d / "dark" / "colors.css").write_text(":root {\n  --primary: #abcdef;\n}\n")
            (d / "light" / "colors.css").write_text(":root {\n  --primary: #123456;\n}\n")
            c = measure.colors_for(d / "light")
            self.assertEqual(c["primary"], (0x12, 0x34, 0x56))
            self.assertEqual(c["dark.primary"], (0xab, 0xcd, 0xef))
            self.assertEqual(measure.colors_for(d / "dark")["dark.primary"], (0xab, 0xcd, 0xef))

    def test_without_neighbouring_dark_palette(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "colors.css").write_text(":root {\n  --primary: #123456;\n}\n")
            self.assertNotIn("dark.primary", measure.colors_for(d))


class TestMissingCapture(unittest.TestCase):
    def test_missing_image(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "layout-gtk3-b3-p0.json").write_text(json.dumps({"toolkit": "gtk3", "batch": 3, "cells": [
                {"row": "checkbox", "state": "normal", "x": 20, "y": 10, "w": 60, "h": 60}]}))
            self.assertEqual(measure.main(d), 1)
            r = json.loads((d / "measurements.json").read_text())
            self.assertEqual(r[0]["deviations"][0]["key"], "capture")


class TestCompare(unittest.TestCase):
    def ok(self, deviations):
        return all(e.ok for e in deviations)

    def test_tolerance_fractional_scale(self):
        spec = {"height": "ButtonSmall.ContainerHeight"}
        self.assertTrue(self.ok(measure.compare(M(height=54), spec, {}, TOKENS, COLORS, 4 / 3, BACKGROUND)))
        self.assertFalse(self.ok(measure.compare(M(height=55), spec, {}, TOKENS, COLORS, 4 / 3, BACKGROUND)))

    def test_hard_coded_number(self):
        self.assertTrue(self.ok(measure.compare(M(height=40), {"height": 30}, {}, TOKENS, COLORS, 4 / 3, BACKGROUND)))

    def test_radius_full(self):
        spec = {"radius": "ButtonSmall.ContainerShapeRound"}
        m = M(height=53, width=150, radius=[26.5, 26, 27, 26.8])
        self.assertTrue(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 4 / 3, BACKGROUND)))
        m = M(height=53, width=150, radius=[12, 12, 12, 12])
        self.assertFalse(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 4 / 3, BACKGROUND)))

    def test_coins(self):
        spec = {"radius": "FilledTextField.ContainerShape"}
        m = M(radius=[5.3, 5.5, 0.2, 0])
        self.assertTrue(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 4 / 3, BACKGROUND)))

    def test_radius_per_corner(self):
        # Split button: full outer corners, inner corners of 4 dp.
        spec = {"radius": ["SplitButtonMedium.ContainerShape", "SplitButtonMedium.InnerCornerCornerSize",
                         "SplitButtonMedium.InnerCornerCornerSize", "SplitButtonMedium.ContainerShape"]}
        m = M(height=56, width=110, radius=[27.6, 4.3, 3.8, 28.2])
        self.assertTrue(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 1, BACKGROUND)))
        m = M(height=56, width=110, radius=[28, 28, 28, 28])
        self.assertFalse(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 1, BACKGROUND)))
        self.assertTrue(self.ok(measure.compare(M(radius=[2, 0, 0, 2]), {"radius": [2, 0, 0, 2]}, {}, TOKENS, COLORS,
                                                1, BACKGROUND)))

    def test_colour_role(self):
        spec = {"background": "FilledTonalButton.ContainerColor", "text": "@on_secondary_container"}
        m = M(background=hexa("#404659"), text=hexa("#dce2f9"))
        self.assertTrue(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 1, BACKGROUND)))
        m = M(background=hexa("#505669"), text=hexa("#dce2f9"))
        self.assertFalse(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 1, BACKGROUND)))

    def test_hover_layer(self):
        normal = {"normal": {"background": "FilledTonalButton.ContainerColor"}}
        spec = {"layer": ("FilledTonalButton.LabelTextColor", "State.HoverStateLayerOpacity")}
        expected = measure.mix(hexa("#404659"), hexa("#dce2f9"), 0.08)
        self.assertTrue(self.ok(measure.compare(M(background=expected), spec, normal, TOKENS, COLORS, 1, BACKGROUND)))
        self.assertFalse(self.ok(measure.compare(M(background=hexa("#404659")), spec, normal, TOKENS, COLORS, 1, BACKGROUND)))

    def test_text_opacity_without_expected_background(self):
        spec = {"text": ("@on_secondary_container", "State.HoverStateLayerOpacity")}
        expected = measure.mix(BACKGROUND, hexa("#dce2f9"), 0.08)
        m = M(background=hexa("#dce2f9"), text=expected)  # lone icon: the measured "background" is the icon
        self.assertTrue(self.ok(measure.compare(m, spec, {}, TOKENS, COLORS, 1, BACKGROUND)))

    def test_compare_dominante(self):
        spec = {"dominant": "@on_secondary_container"}
        self.assertTrue(self.ok(measure.compare(M(dominant=hexa("#dce2f9")), spec, {}, TOKENS, COLORS, 1, BACKGROUND)))
        self.assertFalse(self.ok(measure.compare(M(dominant=hexa("#404659")), spec, {}, TOKENS, COLORS, 1, BACKGROUND)))

    def test_opacity_on_cell_background(self):
        spec = {"background": ("@on_secondary_container", "State.HoverStateLayerOpacity")}
        expected = measure.mix(BACKGROUND, hexa("#dce2f9"), 0.08)
        self.assertTrue(self.ok(measure.compare(M(background=expected), spec, {}, TOKENS, COLORS, 1, BACKGROUND)))


if __name__ == "__main__":
    unittest.main()
