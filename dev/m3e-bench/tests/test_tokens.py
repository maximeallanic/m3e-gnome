import json, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tokens  # noqa: E402

TOKENS_JSON = Path(__file__).resolve().parents[2] / "reference" / "m3e-tokens.json"

SHAPES = """
internal object ShapeTokens {
    val CornerFull = CircleShape
    val CornerMedium = RoundedCornerShape(12.0.dp)
    val CornerExtraSmallTop =
        RoundedCornerShape(
            topStart = 4.0.dp,
            topEnd = 4.0.dp,
            bottomEnd = 0.0.dp,
            bottomStart = 0.0.dp,
        )
    val CornerValueSmall = CornerSize(8.0.dp)
}
"""
TYPO = """
internal object TypeScaleTokens {
    inline val LabelLargeLineHeight: androidx.compose.ui.unit.TextUnit
        get() = 20.0.sp
    inline val LabelLargeSize: androidx.compose.ui.unit.TextUnit
        get() = 14.sp
    inline val LabelLargeTracking: androidx.compose.ui.unit.TextUnit
        get() = 0.1.sp
    inline val LabelLargeWeight: androidx.compose.ui.text.font.FontWeight
        get() = TypefaceTokens.WeightMedium
}
"""
TYPEFACE = """
internal object TypefaceTokens {
    inline val WeightMedium: FontWeight
        get() = FontWeight.Medium
}
"""
ELEV = """
internal object ElevationTokens {
    inline val Level1: androidx.compose.ui.unit.Dp
        get() = 1.0.dp
}
"""


def kt_object(name, body):
    return f"internal object {name}Tokens {{\n{body}\n}}\n"


def one(body, key):
    texts = {"Test": kt_object("Test", body), "Shape": SHAPES, "TypeScale": TYPO,
              "Typeface": TYPEFACE, "Elevation": ELEV}
    raw = {k: tokens.parse_kt(v) for k, v in texts.items()}
    return tokens.resolve(raw)["Test"].get(key)


class TestTokens(unittest.TestCase):
    def test_dp(self):
        self.assertEqual(one("    val ContainerHeight = 40.0.dp", "ContainerHeight"),
                         {"type": "dp", "value": 40.0})

    def test_dp_getter(self):
        body = "    inline val ContainerHeight: androidx.compose.ui.unit.Dp\n        get() = 40.0.dp"
        self.assertEqual(one(body, "ContainerHeight"), {"type": "dp", "value": 40.0})

    def test_getter_inline(self):
        body = "    inline val IconSize: androidx.compose.ui.unit.Dp\n        inline get() = 20.0.dp"
        self.assertEqual(one(body, "IconSize"), {"type": "dp", "value": 20.0})

    def test_role(self):
        self.assertEqual(one("    val ContainerColor = ColorSchemeKeyTokens.SecondaryContainer", "ContainerColor"),
                         {"type": "role", "value": "secondary_container"})

    def test_opacity(self):
        self.assertEqual(one("    const val DisabledContainerOpacity = 0.1f", "DisabledContainerOpacity"),
                         {"type": "opacity", "value": 0.1})

    def test_full_shape(self):
        self.assertEqual(one("    val Shape = ShapeKeyTokens.CornerFull", "Shape"),
                         {"type": "shape", "value": "full", "source": "ShapeKeyTokens.CornerFull"})

    def test_resolved_shape(self):
        self.assertEqual(one("    val Shape = ShapeKeyTokens.CornerMedium", "Shape"),
                         {"type": "dp", "value": 12.0, "source": "ShapeKeyTokens.CornerMedium"})

    def test_shape_corners(self):
        self.assertEqual(one("    val Shape = ShapeKeyTokens.CornerExtraSmallTop", "Shape"),
                         {"type": "corners", "value": [4.0, 4.0, 0.0, 0.0],
                          "source": "ShapeKeyTokens.CornerExtraSmallTop"})

    def test_corner_size(self):
        self.assertEqual(tokens.resolve({"Shape": tokens.parse_kt(SHAPES)})["Shape"]["CornerValueSmall"],
                         {"type": "dp", "value": 8.0})

    def test_elevation(self):
        self.assertEqual(one("    val Elev = ElevationTokens.Level1", "Elev"),
                         {"type": "dp", "value": 1.0, "source": "ElevationTokens.Level1"})

    def test_curve(self):
        body = "    val EasingEmphasizedDecelerateCubicBezier = CubicBezierEasing(0.05f, 0.7f, 0.1f, 1.0f)"
        self.assertEqual(one(body, "EasingEmphasizedDecelerateCubicBezier"),
                         {"type": "curve", "value": [0.05, 0.7, 0.1, 1.0]})

    def test_duration(self):
        self.assertEqual(one("    const val DurationMedium2 = 300.0", "DurationMedium2"),
                         {"type": "ms", "value": 300.0})

    def test_spring_number(self):
        self.assertEqual(one("    const val SpringDefaultSpatialStiffness = 380.0f", "SpringDefaultSpatialStiffness"),
                         {"type": "number", "value": 380.0})

    def test_typography(self):
        self.assertEqual(one("    val LabelTextFont = TypographyKeyTokens.LabelLarge", "LabelTextFont"),
                         {"type": "typography", "value": {"size": 14.0, "line_height": 20.0, "weight": 500,
                                                     "tracking": 0.1},
                          "source": "TypographyKeyTokens.LabelLarge"})

    def test_trailing_comment(self):
        self.assertEqual(one("    val TopSpace = 44.0.dp // TODO: update", "TopSpace"),
                         {"type": "dp", "value": 44.0})

    def test_rectangle(self):
        self.assertEqual(tokens.resolve({"Shape": tokens.parse_kt(
            "internal object ShapeTokens {\n    val CornerNone = RectangleShape\n}\n")})["Shape"]["CornerNone"],
            {"type": "dp", "value": 0.0})

    def test_ref_shape_tokens(self):
        self.assertEqual(one("    val InnerCornerCornerSize = ShapeTokens.CornerValueSmall", "InnerCornerCornerSize"),
                         {"type": "dp", "value": 8.0, "source": "ShapeTokens.CornerValueSmall"})

    def test_unknown_line_ignored(self):
        self.assertIsNone(one("    val Foo = something()", "Foo"))

    def test_shell_tokens_present(self):
        t = json.loads(TOKENS_JSON.read_text(encoding="utf-8"))
        self.assertEqual(t["SearchBar"]["ContainerHeight"], {"type": "dp", "value": 56.0})
        self.assertEqual(t["DatePickerModal"]["DateContainerHeight"], {"type": "dp", "value": 40.0})
        for comp in ("FilledCard", "ElevatedCard"):
            self.assertIn("ContainerShape", t[comp])
        self.assertTrue(any("Toolbar" in c for c in t), "floating toolbar tokens missing")
        self.assertTrue(any("ButtonGroup" in c for c in t), "button group tokens missing")

    def test_reference_schema_is_english(self):
        # The generator and every reader use the English schema: the committed reference file must match it.
        t = json.loads(TOKENS_JSON.read_text(encoding="utf-8"))
        types = {"dp", "sp", "role", "opacity", "number", "ms", "curve", "shape", "corners", "weight", "typography"}
        for comp, keys in t.items():
            for key, token in keys.items():
                self.assertIn(token["type"], types, f"{comp}.{key}")
                self.assertIn("value", token, f"{comp}.{key}")
                if token["type"] == "typography":
                    self.assertEqual(set(token["value"]), {"size", "line_height", "weight", "tracking"},
                                     f"{comp}.{key}")


if __name__ == "__main__":
    unittest.main()
