#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Print, per frame, how much a box of a screen recording changed.

Usage: activity.py VIDEO X0 Y0 X1 Y1
Output TSV: frame  t_s  diff_vs_previous  diff_vs_first  mean_luma
Coordinates are device pixels of the recording. Needs ffmpeg and ffprobe.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_frames import read_gray_frames  # noqa: E402


def activity(times, frames, box):
    """Rows (frame, t_s, mean |frame - previous|, mean |frame - first|, mean luma) of the box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    region = frames[:, y0:y1, x0:x1].astype(np.int16)
    rows = []
    for i, t in enumerate(times[:len(region)]):
        previous = region[i - 1] if i else region[0]
        rows.append((i, float(t), float(np.abs(region[i] - previous).mean()),
                     float(np.abs(region[i] - region[0]).mean()), float(region[i].mean())))
    return rows


def main(argv):
    if len(argv) != 6:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    times, frames = read_gray_frames(argv[1])
    for i, t, d_prev, d_first, luma in activity(times, frames, tuple(map(int, argv[2:6]))):
        print(f"{i}\t{t:.3f}\t{d_prev:.2f}\t{d_first:.2f}\t{luma:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
