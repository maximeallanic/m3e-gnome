import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ink_grid as g  # noqa: E402


class RulePxTest(unittest.TestCase):
    CSS = '''
/* #panel .panel-button .system-status-icon { icon-size: 99px; } (a comment, ignored) */
#panel .panel-button .system-status-icon {
  color: {{colors.on_surface.default.hex}};
  icon-size: 20px; /* XSmallIconButton.IconSize */
}
#panel .panel-button.clock-display .clock,
#panel:overview .panel-button.clock-display .clock {
  font-size: 16px; /* TypeScale.TitleMediumSize */
  min-font-size: 3px;
}
#panel .panel-button .system-status-icon {
  padding: 0;
  icon-size: 16px; /* later rule wins */
}
'''

    def test_last_rule_wins_and_comments_are_ignored(self):
        self.assertEqual(g.rule_px(self.CSS, '#panel .panel-button .system-status-icon', 'icon-size'), 16)

    def test_selector_inside_a_list(self):
        self.assertEqual(g.rule_px(self.CSS, '#panel .panel-button.clock-display .clock', 'font-size'), 16)

    def test_property_name_is_exact(self):
        css = '.x { min-font-size: 3px; }'
        with self.assertRaises(LookupError):
            g.rule_px(css, '.x', 'font-size')

    def test_selector_must_match_exactly(self):
        with self.assertRaises(LookupError):
            g.rule_px(self.CSS, '.system-status-icon', 'icon-size')


class TargetsTest(unittest.TestCase):
    def test_grid_sizes(self):
        shell = ('stage { font-size: 14px; }\n'
                 '#panel .panel-button.clock-display .clock { font-size: 16px; }\n'
                 '#panel .panel-button .system-status-icon { icon-size: 16px; }\n')
        gtk4 = 'headerbar button:not(#m3e).image-button { -gtk-icon-size: 10px; }'
        t = g.targets(0.716, shell, gtk4)
        self.assertAlmostEqual(t['bar_ink'], 11.456)
        self.assertAlmostEqual(t['bar_icon_expected'], 0.716 * 16 / 0.72)
        self.assertEqual((t['bar_icon'], t['header_icon']), (16, 10))
        self.assertAlmostEqual(t['header_ink'], 10.024)

    def test_repository_sheets_declare_the_grid_sizes(self):
        shell, gtk4 = g.shell_css(), g.gtk4_css()
        for css, (selector, prop) in ((shell, g.BODY_TEXT), (shell, g.CLOCK), (shell, g.BAR_ICON),
                                      (gtk4, g.HEADER_ICON)):
            self.assertGreater(g.rule_px(css, selector, prop), 0)


class WeightTest(unittest.TestCase):
    def test_app_weight_matches_the_stroke_ratio(self):
        # stroke grows 20 units per weight step, square height 700: 0.15 * 700 = 105 -> weight 600 (100 units)
        stroke = {300: 40, 400: 60, 500: 80, 600: 100, 700: 120}
        self.assertEqual(g.app_weight(stroke.get, lambda w: 700), 600)

    def test_status_weight_accounts_for_scaling(self):
        stroke = {300: 40, 400: 60, 500: 80, 600: 100, 700: 120}.get
        # A small symbol is scaled up a lot to reach the common height, so it needs a light weight; a large one a heavy
        # weight. Target stroke: 0.15 * 0.72 = 0.108 of the frame side.
        small = g.status_weight([0, 0, 200, 200], stroke)
        large = g.status_weight([0, 0, 800, 800], stroke)
        self.assertEqual(small, 300)
        self.assertEqual(large, 700)
        self.assertIn(g.status_weight([0, 0, 600, 600], stroke), g.WEIGHTS)


if __name__ == '__main__':
    unittest.main()
