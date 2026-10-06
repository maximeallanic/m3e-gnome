"""Pure tests of the pixel measurement tools on synthetic data (no phone, no recording); the video test needs
ffmpeg and is skipped without it. Run: uv run --with numpy python -m unittest -v test_pixel_measure (from tests/)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import activity  # noqa: E402
import displacement  # noqa: E402
import fit_spring  # noqa: E402
from video_frames import read_gray_frames  # noqa: E402


def moving_square_frames(n=24, size=(64, 96), box=24):
    """Frames of a bright square sliding down 2 px per frame, then still: returns (frames, final (x, y))."""
    frames = np.zeros((n, size[0], size[1]), np.uint8)
    y_final = 30
    for i in range(n):
        y = min(y_final, 4 + 2 * i)
        frames[i, y:y + box, 30:30 + box] = np.arange(box, dtype=np.uint8)[None, :] * 8 + 40
    return frames, (30, y_final)


class FitSpringTest(unittest.TestCase):
    def test_underdamped_curve_is_recovered(self):
        t = np.arange(0, 1.0, 1 / 88)
        x = fit_spring.spring(t - 0.05, 0.8, 380.0, 40.0, 0.0)
        x[t < 0.05] = 40.0
        err, zeta, k, ts, x0 = fit_spring.fit(t, x)
        self.assertLess(err, 0.5)
        self.assertAlmostEqual(zeta, 0.8, delta=0.06)
        self.assertAlmostEqual(k, 380.0, delta=40.0)
        self.assertAlmostEqual(x0, 40.0, delta=2.0)

    def test_spring_converges_for_every_damping_regime(self):
        t = np.array([0.0, 5.0])
        for zeta in (0.5, 1.0, 1.5):
            x = fit_spring.spring(t, zeta, 400.0, 10.0, 0.0)
            self.assertAlmostEqual(x[0], 10.0, places=6)
            self.assertAlmostEqual(x[1], 0.0, places=6)


class ActivityTest(unittest.TestCase):
    def test_still_box_has_no_activity_and_moving_box_has(self):
        frames, _ = moving_square_frames()
        times = np.arange(len(frames)) / 60
        rows = activity.activity(times, frames, (0, 0, 96, 64))
        self.assertEqual(rows[0][2], 0.0)
        self.assertGreater(rows[3][2], 0.0)      # still sliding
        self.assertEqual(rows[-1][2], 0.0)       # settled


class DisplacementTest(unittest.TestCase):
    def test_slide_is_measured_in_dp(self):
        frames, (x, y) = moving_square_frames()
        times = np.arange(len(frames)) / 60
        rows = displacement.displacement(times, frames, (x, y, x + 24, y + 24), max_dy=40, max_dx=0, step=2, dp=2.0)
        self.assertEqual(len(rows), len(frames))
        # first frames: the square is 26 px above its final place = 13 dp at 2 px/dp
        self.assertAlmostEqual(rows[0][1], -13.0, delta=1.0)
        self.assertAlmostEqual(rows[-1][1], 0.0, delta=0.01)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg not installed")
    def test_frames_of_a_real_video_file(self):
        frames, _ = moving_square_frames(n=12)
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / "slide.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "96x64", "-r", "30",
                            "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)],
                           input=frames.tobytes(), check=True)
            times, decoded = read_gray_frames(str(video))
        self.assertEqual(decoded.shape[1:], (64, 96))
        self.assertEqual(len(times), len(decoded))
        self.assertGreaterEqual(len(decoded), 10)


if __name__ == "__main__":
    unittest.main()
