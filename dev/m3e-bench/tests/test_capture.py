import sys, unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import capture  # noqa: E402
from gi.repository import GLib  # noqa: E402

TYPE = "(ua((ssss)a(siiddada{sv})a{sv})a(iiduba(ssss)a{sv})a{sv})"


class TestCapture(unittest.TestCase):
    def test_parse_displayconfig_state(self):
        text = (ICI / "tests/data/displayconfig.gvariant").read_text()
        screens = capture.screens_from(GLib.Variant.parse(GLib.VariantType(TYPE), text))
        self.assertEqual(len(screens), 1)
        e = screens[0]
        self.assertEqual(e.name, "eDP-1")
        self.assertAlmostEqual(e.scale, 4 / 3, places=4)
        self.assertTrue(e.primary)
        self.assertEqual((e.x, e.y), (0, 0))
        self.assertAlmostEqual(e.width * e.scale, 2256, delta=0.5)
        self.assertAlmostEqual(e.height * e.scale, 1504, delta=0.5)

    def test_area_one_screen(self):
        e = capture.Screen("eDP-1", 0, 0, 1692, 1128, 4 / 3, True)
        self.assertEqual(capture.screen_area([e], e, 2256), (0, 0, 2256, 1504))

    def test_area_two_screens(self):
        a = capture.Screen("eDP-1", 0, 0, 1692, 1128, 4 / 3, False)
        b = capture.Screen("DP-1", 1692, 0, 3413, 960, 1.5, True)
        # capture at the highest scale: 1.5 px per logical px
        png_width = round((1692 + 3413) * 1.5)
        self.assertEqual(capture.screen_area([a, b], b, png_width), (2538, 0, 5120, 1440))


class TestTargetScreen(unittest.TestCase):
    def test_highest_scale(self):
        a = capture.Screen("eDP-1", 1920, 1440, 1280, 800, 1.5, False)
        b = capture.Screen("DP-3", 0, 0, 5120, 1440, 1.0, True)
        self.assertEqual(capture.target_screen([b, a]).name, "eDP-1")

    def test_tie_primary(self):
        a = capture.Screen("eDP-1", 0, 0, 1692, 1128, 4 / 3, False)
        b = capture.Screen("DP-3", 1692, 0, 3840, 1080, 4 / 3, True)
        self.assertEqual(capture.target_screen([a, b]).name, "DP-3")

    def test_image_scale(self):
        a = capture.Screen("eDP-1", 1920, 1440, 1280, 800, 1.5, False)
        b = capture.Screen("DP-3", 0, 0, 5120, 1440, 1.0, True)
        self.assertAlmostEqual(capture.image_scale([a, b], 7680), 1.5)
        self.assertEqual(capture.screen_area([a, b], a, 7680), (2880, 2160, 1920, 1200))


if __name__ == "__main__":
    unittest.main()
