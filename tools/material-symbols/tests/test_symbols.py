import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import map as status_map  # noqa: E402
import map_apps  # noqa: E402
import symbols as s  # noqa: E402


class NamingTest(unittest.TestCase):
    def test_cache_and_remote_names(self):
        self.assertEqual(s.cache_name('!wifi'), 'wifi_fill1.svg')
        self.assertEqual(s.cache_name('wifi', 20), 'wifi_20px.svg')
        self.assertEqual(s.cache_name('!wifi', 20), 'wifi_fill1_20px.svg')
        self.assertEqual(s.remote_names('!wifi'), ['wifi_fill1_24px.svg', 'wifi_24px.svg'])
        self.assertEqual(s.remote_names('home', 20), ['home_20px.svg'])


class FramingTest(unittest.TestCase):
    def test_status_viewbox_height_limited(self):
        vb, ink = s.status_viewbox([100, -800, 200, 360], 0.72)
        self.assertEqual(vb, '-50.0 -870.0 500.0 500.0')       # side = 360 / .72 = 500, centred on (200, -620)
        self.assertAlmostEqual(ink, 0.4)

    def test_status_viewbox_width_limited(self):
        vb, ink = s.status_viewbox([0, -700, 900, 100], 0.72)
        self.assertEqual(vb.split()[2], '900.0')
        self.assertEqual(ink, 1.0)

    def test_app_viewbox(self):
        self.assertEqual(s.app_viewbox([200, -760, 560, 560], 110), '110 -850 740 740')   # tightened by the inset
        self.assertEqual(s.app_viewbox([0, -960, 960, 960], 110), '0 -960 960 960')       # full-size symbol widens
        self.assertEqual(s.app_viewbox([200, -760, 560, 560], 110, 0.5), '-260 -1220 1480 1480')

    def test_app_viewbox_tolerates_small_overflow(self):
        self.assertEqual(s.app_viewbox([95, -760, 770, 560], 110), '110 -850 740 740')


class SvgTest(unittest.TestCase):
    def test_extract_paths(self):
        src = '<svg><path d="M0 0"/><path d="M1 1"/></svg>'
        self.assertEqual(s.extract_paths(src), '<path fill="#2e3436" d="M0 0"/><path fill="#2e3436" d="M1 1"/>')
        self.assertIn('fill-opacity="0.3"', s.extract_paths(src, 0.3))

    def test_markers(self):
        self.assertIn('matrix(1 0 0 -1 0 -960)', s.transform_app_paths('<path/>', '^sort'))
        self.assertIn('rotate(90', s.transform_app_paths('<path/>', '%x'))
        self.assertEqual(s.transform_app_paths('<path/>', 'x'), '<path/>')

    def test_status_svg_ink_width(self):
        self.assertIn('data-ink-width="0.500"', s.status_svg('0 0 1 1', '', 0.5))
        self.assertNotIn('data-ink-width', s.status_svg('0 0 1 1', ''))


class MapsTest(unittest.TestCase):
    def test_every_value_is_a_symbol_name(self):
        for v in status_map.M.values():
            self.assertRegex(v.lstrip('!'), r'^[a-z0-9_]+$')
        for _, ms in map_apps.A.values():
            self.assertRegex(ms.lstrip('!^%'), r'^[a-z0-9_]+$')

    def test_partial_levels_have_an_underlay_and_a_frame(self):
        for level in ('network-wireless-signal-ok', 'network-wireless-signal-weak',
                      'network-cellular-signal-ok', 'network-cellular-signal-weak'):
            v = status_map.M[level + '-symbolic']
            self.assertIn(v, status_map.UNDERLAY)
            self.assertEqual(status_map.UNDERLAY[v], status_map.FAMILY[v])
            self.assertIn(status_map.UNDERLAY[v], status_map.M.values())

    def test_scaled_icons_exist(self):
        self.assertTrue(set(map_apps.SCALE) <= set(map_apps.A))


if __name__ == '__main__':
    unittest.main()
