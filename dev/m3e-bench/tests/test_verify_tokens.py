import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verify_tokens import verify, compare_blocks, main  # noqa: E402

T = {
    "ButtonSmall": {"ContainerHeight": {"type": "dp", "value": 40.0},
                    "LeadingSpace": {"type": "dp", "value": 16.0},
                    "ContainerShapeRound": {"type": "shape", "value": "full"}},
    "FilledTextField": {"ContainerShape": {"type": "corners", "value": [4.0, 4.0, 0.0, 0.0]}},
    "State": {"HoverStateLayerOpacity": {"type": "opacity", "value": 0.08}},
    "Tab": {"ContainerShape": {"type": "dp", "value": 0.0}},
    "Motion": {"DurationShort4": {"type": "ms", "value": 200.0},
               "EasingStandardCubicBezier": {"type": "curve", "value": [0.2, 0.0, 0.0, 1.0]}},
    "FilledTonalButton": {"LabelTextFont": {"type": "typography", "value": {"size": 14.0, "line_height": 20.0,
                                                                         "weight": 500, "tracking": 0.1}}},
}


def block(*lines):
    return "button {\n" + "\n".join("  " + l for l in lines) + "\n}\n"


class TestVerify(unittest.TestCase):
    def test_right_value(self):
        self.assertEqual(verify(block("min-height: 40px; /* ButtonSmall.ContainerHeight */"), T, "gtk4"), [])

    def test_wrong_value(self):
        e = verify(block("min-height: 36px; /* ButtonSmall.ContainerHeight */"), T, "gtk4")
        self.assertEqual(len(e), 1)
        self.assertIn("36", e[0]); self.assertIn("40", e[0])

    def test_unknown_token(self):
        e = verify(block("min-height: 40px; /* ButtonSmall.Height */"), T, "gtk4")
        self.assertEqual(len(e), 1); self.assertIn("ButtonSmall.Height", e[0])

    def test_no_comment(self):
        self.assertEqual(len(verify(block("min-height: 36px;"), T, "gtk4")), 1)

    def test_zero_token(self):
        self.assertEqual(verify(block("border-radius: 0; /* Tab.ContainerShape */"), T, "gtk4"), [])
        self.assertEqual(len(verify(block("border-radius: 4px; /* Tab.ContainerShape */"), T, "gtk4")), 1)

    def test_zero_without_comment(self):
        self.assertEqual(verify(block("margin: 0;", "padding: 0px;"), T, "gtk4"), [])

    def test_visual_accepted(self):
        self.assertEqual(verify(block("margin: 4px; /* M3E-visual: icon/text gap measured on the image */"),
                                  T, "gtk4"), [])

    def test_visual_without_reason(self):
        self.assertEqual(len(verify(block("margin: 4px; /* M3E-visual: */"), T, "gtk4")), 1)

    def test_full_shape(self):
        self.assertEqual(verify(block("border-radius: 9999px; /* ButtonSmall.ContainerShapeRound */"), T, "gtk4"), [])
        self.assertEqual(len(verify(block("border-radius: 20px; /* ButtonSmall.ContainerShapeRound */"),
                                      T, "gtk4")), 1)

    def test_corners(self):
        self.assertEqual(verify(block("border-radius: 4px 4px 0 0; /* FilledTextField.ContainerShape */"),
                                  T, "gtk4"), [])

    def test_several_tokens(self):
        self.assertEqual(verify(block("padding: 0 16px; /* ButtonSmall.LeadingSpace */"), T, "gtk4"), [])
        self.assertEqual(verify(block("padding: 0 16px 0 16px; /* ButtonSmall.LeadingSpace ButtonSmall.LeadingSpace */"),
                                  T, "gtk4"), [])

    def test_extra_number(self):
        self.assertEqual(len(verify(block("padding: 8px 16px; /* ButtonSmall.LeadingSpace */"), T, "gtk4")), 1)

    def test_opacity_in_alpha(self):
        self.assertEqual(verify(block("background-image: image(alpha(@on_surface, 0.08)); "
                                       "/* State.HoverStateLayerOpacity */"), T, "gtk3"), [])

    def test_pinned_token_in_gradient(self):
        grad = "background-image: radial-gradient(circle 10px at 0 0, alpha(@on_surface, 0.08) 9.5px, alpha(@s, 0) 10px);"
        self.assertEqual(verify(block(grad + " /* State.HoverStateLayerOpacity@0.08 */ "), T, "gtk3"),
                         ["2: background-image: value with no token: 10 9.5 10"])
        self.assertEqual(verify(block(grad + " /* M3E-visual: radii are not tokens; State.HoverStateLayerOpacity@0.08 */"),
                                T, "gtk3"), [])

    def test_pinned_token_wrong_value(self):
        grad = "background-image: image(alpha(@on_surface, 0.1));"
        self.assertEqual(verify(block(grad + " /* M3E-visual: x; State.HoverStateLayerOpacity@0.1 */"), T, "gtk3"),
                         ["2: background-image: State.HoverStateLayerOpacity@0.1: the token is 0.08"])

    def test_pinned_value_absent(self):
        grad = "background-image: image(alpha(@on_surface, 0.1));"
        self.assertEqual(verify(block(grad + " /* M3E-visual: x; State.HoverStateLayerOpacity@0.08 */"), T, "gtk3"),
                         ["2: background-image: State.HoverStateLayerOpacity@0.08: 0.08 is not on the declaration"])

    def test_pinned_unknown_token(self):
        grad = "background-image: image(alpha(@on_surface, 0.08));"
        self.assertIn("unknown token: State.Nope", verify(block(grad + " /* State.Nope@0.08 */"), T, "gtk3")[0])

    def test_pinned_with_positional_token(self):
        self.assertEqual(verify(block("padding: 8px 16px; /* ButtonSmall.LeadingSpace@16 */"), T, "gtk4"),
                         ["2: padding: value with no token: 8"])
        self.assertEqual(verify(block("padding: 16px 16px; /* ButtonSmall.LeadingSpace@16 */"), T, "gtk4"), [])

    def test_transition(self):
        self.assertEqual(verify(block("transition: background-color 200ms cubic-bezier(0.2, 0, 0, 1); "
                                       "/* Motion.DurationShort4 Motion.EasingStandardCubicBezier */"), T, "gtk4"), [])

    def test_typography(self):
        self.assertEqual(verify(block("font-size: 14px; /* FilledTonalButton.LabelTextFont.size */",
                                       "font-weight: 500; /* FilledTonalButton.LabelTextFont.weight */"), T, "gtk4"), [])

    def test_full_opacity(self):
        self.assertEqual(verify(block("opacity: 1;"), T, "gtk4"), [])

    def test_no_hard_coded_colour(self):
        self.assertEqual(len(verify(block("background-color: #ffffff;"), T, "gtk4")), 1)
        self.assertEqual(len(verify(block("color: rgba(0, 0, 0, 0.5);"), T, "gtk4")), 1)
        self.assertEqual(len(verify(block("color: white;"), T, "gtk4")), 1)
        self.assertEqual(verify(block("background-color: @primary;", "color: transparent;"), T, "gtk3"), [])

    def test_gtk3_no_var(self):
        self.assertEqual(len(verify(block("color: var(--primary);"), T, "gtk3")), 1)
        self.assertEqual(verify(block("color: var(--primary);"), T, "gtk4"), [])

    def test_gtk3_calc_accepted(self):
        # GTK 3.24 parses calc() (checked with verify_css); only var() is specific to GTK 4
        self.assertEqual(verify(block("background-position: calc(100% - 0px) 0;"), T, "gtk3"), [])

    def test_line_number(self):
        e = verify("a {}\n" + block("min-height: 36px;"), T, "gtk4")
        self.assertTrue(e[0].startswith("3:"), e)

    def test_different_blocks(self):
        a = "/* == buttons == */\n/* == switch == */\n"
        b = "/* == switch == */\n/* == buttons == */\n"
        self.assertEqual(len(compare_blocks(a, b)), 1)
        self.assertEqual(compare_blocks(a, a), [])


# St dialect (Shell sheet, matugen template): {{...}} ignored, no bold, !important restricted.
MATUGEN_RGBA = ("rgba({{colors.on_surface.default.red}}, {{colors.on_surface.default.green}}, "
                "{{colors.on_surface.default.blue}}, 0.08)")


def st_sheet(*blocks):
    return "\n".join(blocks) + "\n"


class TestStDialect(unittest.TestCase):
    def test_matugen_ignored(self):
        css = block("color: {{colors.on_surface.default.hex}};",
                   f"background-color: {MATUGEN_RGBA}; /* State.HoverStateLayerOpacity */")
        self.assertEqual(verify(css, T, "st"), [])

    def test_matugen_alpha_without_token(self):
        self.assertEqual(len(verify(block(f"background-color: {MATUGEN_RGBA};"), T, "st")), 1)

    def test_hard_coded_colour(self):
        self.assertEqual(len(verify(block("color: #ffffff;"), T, "st")), 1)
        self.assertEqual(len(verify(block("color: rgba(0, 0, 0, 0.5);"), T, "st")), 1)

    def test_bold_reported(self):
        for v in ("700", "bold", "bolder", "500"):
            e = verify(block(f"font-weight: {v};"), T, "st")
            self.assertEqual(len(e), 1, v)
            self.assertIn("font-weight", e[0])
        self.assertEqual(verify(block("font-weight: normal;"), T, "st"), [])
        self.assertEqual(verify(block("font-weight: 400; /* M3E-visual: weight of Body */"), T, "st"), [])

    def test_bold_any_weight_above_400(self):
        # User rule "no bold": any weight > 400, not only the hundreds 500-900.
        for v in ("401", "450", "550", "599", "650", "1000", "bold !important"):
            e = verify(block(f"font-weight: {v}; /* M3E-visual: trial */"), T, "st")
            self.assertTrue(any("font-weight > 400" in x for x in e), v)
        for v in ("100", "300", "400", "lighter"):
            e = verify(block(f"font-weight: {v}; /* M3E-visual: trial */"), T, "st")
            self.assertFalse(any("font-weight > 400" in x for x in e), v)

    def test_bold_in_font_shorthand(self):
        for v in ("bold 14px \"Google Sans Flex\"", "600 14px sans-serif"):
            e = verify(block(f"font: {v}; /* M3E-visual: trial */"), T, "st")
            self.assertTrue(any("bold" in x or "> 400" in x for x in e), v)
        e = verify(block("font: 400 14px sans-serif; /* M3E-visual: trial */"), T, "st")
        self.assertEqual(e, [])

    def test_single_line_rule(self):
        # A rule written on a single line is checked like the others (bold, !important, colours).
        e = verify(st_sheet("/* == Base == */", "* { font-weight: 700 !important; }"), T, "st")
        self.assertTrue(any("font-weight > 400" in x for x in e), e)
        e = verify(st_sheet("/* == Base == */", "stage { color: #ffffff; }"), T, "st")
        self.assertEqual(len(e), 1)
        e = verify(st_sheet("/* == Base == */", ".a { color: {{colors.primary.default.hex}} !important; }"),
                     T, "st")
        self.assertTrue(any("!important" in x for x in e), e)
        # No-bold rule on one line: accepted; bold in any block, on one line: refused.
        self.assertEqual(verify(st_sheet("/* == Base == */", "* { font-weight: normal !important; }"),
                                  T, "st"), [])
        css = st_sheet("/* == Flat surfaces == */", ".x { font-weight: 600; }")
        self.assertEqual(len(verify(css, T, "st")), 1)
        # Declaration glued to the opening or closing brace of a multi-line rule.
        css = st_sheet("/* == Base == */", "stage { font-weight: bold;\n  color: {{colors.primary.default.hex}};\n}")
        self.assertEqual(len(verify(css, T, "st")), 1)
        css = st_sheet("/* == Base == */", "stage {\n  color: {{colors.primary.default.hex}};\n  font-weight: 800; }")
        self.assertEqual(len(verify(css, T, "st")), 1)
        # One-line rule with a token at the end of the line (single declaration): checked like a lone declaration.
        self.assertEqual(verify("button { min-height: 40px; } /* ButtonSmall.ContainerHeight */\n", T, "st"), [])
        self.assertEqual(len(verify("button { min-height: 36px; } /* ButtonSmall.ContainerHeight */\n", T, "st")), 1)
        # Declaration followed by "}" on the same line: the rule is closed, the next selector ("*" alone on its
        # line, brace on the next line) is read correctly, and the no-bold rule is recognised.
        for tail in ("}", " }", "} /* end */"):
            css = st_sheet("/* == Base == */",
                             f"stage {{\n  color: {{{{colors.primary.default.hex}}}};{tail}\n*\n{{\n"
                             "  font-weight: normal !important;\n}")
            self.assertEqual([e for e in verify(css, T, "st") if "!important" in e], [], tail)
        css = st_sheet("/* == Base == */", "stage {\n  color: {{colors.primary.default.hex}}; }\n"
                         "  font-weight: 700;\n")
        self.assertEqual(len(verify(css, T, "st")), 1)
        # Selector with a pseudo-class on one line: not taken for a declaration.
        self.assertEqual(verify(st_sheet("/* == Base == */",
                                             ".a:hover { color: {{colors.primary.default.hex}}; }"), T, "st"), [])

    def test_important_outside_exemption(self):
        e = verify(st_sheet("/* == Base == */", block("color: {{colors.primary.default.hex}} !important;")),
                     T, "st")
        self.assertEqual(len(e), 1)
        self.assertIn("!important", e[0])

    def test_important_marked_exception(self):
        # Targeted exception: !important allowed outside the exemptions on a marked line, with a reason.
        css = st_sheet("/* == Calendar == */", block(
            "color: {{colors.on_primary.default.hex}} !important; /* important-exception: beats the stock sheet */"))
        self.assertEqual(verify(css, T, "st"), [])
        # Marker without a reason: refused.
        css = st_sheet("/* == Calendar == */", block(
            "color: {{colors.on_primary.default.hex}} !important; /* important-exception: */"))
        self.assertEqual(len(verify(css, T, "st")), 1)
        # Other comment (token, M3E-visual): still refused.
        css = st_sheet("/* == Calendar == */", block(
            "color: {{colors.on_primary.default.hex}} !important; /* M3E-visual: reason */"))
        self.assertEqual(len(verify(css, T, "st")), 1)
        # The marker does not exempt from the tokens: a number without a token is still reported.
        css = st_sheet("/* == Calendar == */", block(
            "border-radius: 12px !important; /* important-exception: reason */"))
        self.assertEqual(len(verify(css, T, "st")), 1)

    def test_important_no_bold_rule(self):
        css = st_sheet("/* == Base == */", "* {\n  font-weight: normal !important;\n}")
        self.assertEqual(verify(css, T, "st"), [])
        # Same declaration under another selector: refused.
        css = st_sheet("/* == Base == */", "stage {\n  font-weight: normal !important;\n}")
        self.assertEqual(len(verify(css, T, "st")), 1)

    def test_flat_surface_border(self):
        # The border of the flat surfaces is the documented !important exception; elsewhere it is refused.
        css = st_sheet("/* == Flat surfaces == */", "#panel .panel-button {\n  border: none !important;\n}")
        self.assertEqual(verify(css, T, "st"), [])
        css = st_sheet("/* == Flat surfaces == */", "#panel {\n  border: 1px solid !important;\n}")
        self.assertEqual(len(verify(css, T, "st")), 1)
        css = st_sheet("/* == Menus == */", "#panel {\n  border: none !important;\n}")
        self.assertEqual(len(verify(css, T, "st")), 1)

    def test_multi_line_comment_is_not_a_selector(self):
        # The words of a comment spread over several lines must not become the selector of the next rule.
        css = st_sheet("/* == No bold == */", "/* Long comment about the rule below,\n   with a colon: and !important. */",
                       "* {\n  font-weight: normal !important;\n}")
        self.assertEqual(verify(css, T, "st"), [])
        # A trailing comment spread over two lines still belongs to its declaration.
        self.assertEqual(verify("button {\n  margin: 4px; /* M3E-visual: gap measured\n  on the image */\n}\n", T, "gtk4"), [])

    def test_gtk_unchanged(self):
        # The St rules do not apply to GTK sheets (button weight 500, tokenised).
        self.assertEqual(verify(block("font-weight: 500; /* FilledTonalButton.LabelTextFont.weight */"),
                                  T, "gtk4"), [])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.d = Path(self.folder.name)
        (self.d / "tokens.json").write_text(json.dumps(T))

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        (self.d / name).write_text(text)
        return str(self.d / name)

    def test_one_st_sheet(self):
        f = self.write("m3e-shell-template.css", st_sheet(
            "/* == Base == */", "stage {\n  color: {{colors.on_surface.default.hex}};\n}"))
        self.assertEqual(main([str(self.d / "tokens.json"), f]), 0)
        g = self.write("broken-shell.css", block("font-weight: 700;"))
        self.assertEqual(main([str(self.d / "tokens.json"), g]), 1)

    def test_two_gtk_sheets(self):
        # gtk3 + gtk4 sheets with --compare-blocks: the block titles must match.
        a = self.write("m3e-gtk3.css", "/* == buttons == */\n" + block("min-height: 40px; /* ButtonSmall.ContainerHeight */"))
        b = self.write("m3e-gtk4.css", "/* == buttons == */\n" + block("min-height: 40px; /* ButtonSmall.ContainerHeight */"))
        self.assertEqual(main(["--compare-blocks", str(self.d / "tokens.json"), a, b]), 0)
        c = self.write("other-gtk4.css", "/* == switch == */\n")
        self.assertEqual(main(["--compare-blocks", str(self.d / "tokens.json"), a, c]), 1)
        # Without the flag the titles are not compared.
        self.assertEqual(main([str(self.d / "tokens.json"), a, c]), 0)

    def test_three_sheets(self):
        a = self.write("m3e-gtk3.css", "/* == buttons == */\n")
        b = self.write("m3e-gtk4.css", "/* == buttons == */\n")
        s = self.write("m3e-shell-template.css", "/* == Base == */\n" + block("color: #000000;"))
        self.assertEqual(main([str(self.d / "tokens.json"), a, b, s]), 1)


if __name__ == "__main__":
    unittest.main()
