import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reference_images  # noqa: E402

PAGE = '''<main><img alt="Logo" src="https://firebasestorage.googleapis.com/logo.png">
<img alt="Filled button states." src="https://lh3.googleusercontent.com/AbC_d-1">
<img alt="Diagram of corner radii of buttons." src="https://lh3.googleusercontent.com/XyZ=w400">
<img src="https://lh3.googleusercontent.com/noalt"></main>'''


class TestReferenceImages(unittest.TestCase):
    def test_extracts_only_lh3(self):
        imgs = reference_images.extract(PAGE)
        self.assertEqual([a for a, _ in imgs], ["Filled button states.", "Diagram of corner radii of buttons.", ""])

    def test_full_resolution_url(self):
        imgs = reference_images.extract(PAGE)
        self.assertEqual(imgs[1][1], "https://lh3.googleusercontent.com/XyZ=s0")
        self.assertEqual(imgs[0][1], "https://lh3.googleusercontent.com/AbC_d-1=s0")

    def test_file_name(self):
        self.assertEqual(reference_images.file_name(3, "Diagram of corner radii of buttons."),
                         "03-diagram-of-corner-radii-of-buttons")
        self.assertEqual(reference_images.file_name(12, ""), "12-image")


if __name__ == "__main__":
    unittest.main()
