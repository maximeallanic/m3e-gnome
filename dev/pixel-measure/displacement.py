#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Measure how a region of a screen recording moves over time.

Estimates, for every frame, the translation (dx, dy) of a rectangular region of the LAST frame (the settled state)
by brute-force matching, plus its mean absolute difference (residual: high = the region is fading or morphing, not
just moving). Coordinates are device pixels; --dp divides them for output (px per dp of the recorded device).

Usage: displacement.py VIDEO X0 Y0 X1 Y1 [--max-dy N] [--max-dx N] [--dp 3]
Output TSV: t_ms  dy  dx  residual  (t relative to the first frame that moved)
Needs ffmpeg and ffprobe.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_frames import read_gray_frames  # noqa: E402


def best_shift(frame, ref, box, max_dy, max_dx, step):
    """(residual, dy, dx) minimising the mean |frame shifted by (dy, dx) - ref| over the box; coarse search every
    `step` px, then refined by +-step around the best candidate."""
    x0, y0, x1, y1 = box
    height, width = frame.shape

    def cost(dy, dx):
        ya, xa = y0 + dy, x0 + dx
        if ya < 0 or xa < 0 or ya + (y1 - y0) > height or xa + (x1 - x0) > width:
            return 1e9
        return float(np.abs(frame[ya:ya + y1 - y0, xa:xa + x1 - x0] - ref).mean())

    coarse = min((cost(dy, dx), dy, dx)
                 for dy in range(-max_dy, max_dy + 1, step) for dx in range(-max_dx, max_dx + 1, step))
    _, dy, dx = coarse
    return min((cost(dy + i, dx + j), dy + i, dx + j)
               for i in range(-step, step + 1) for j in range(-step, step + 1))


def displacement(times, frames, box, max_dy=0, max_dx=0, step=2, dp=3.0, target="last", t_min=0.0, t_max=1e9):
    """Rows (t_ms, dy_dp, dx_dp, residual); t_ms is relative to the first frame that moved."""
    keep = (times >= t_min) & (times <= t_max)
    times, frames = times[keep], frames[keep].astype(np.int16)
    x0, y0, x1, y1 = box
    ref = (frames[-1] if target == "last" else frames[0])[y0:y1, x0:x1]
    res = [best_shift(f, ref, box, max_dy, max_dx, step) for f in frames]
    moving = [i for i in range(1, len(res)) if res[i][1:] != res[i - 1][1:] or abs(res[i][0] - res[i - 1][0]) > 0.5]
    start = times[moving[0] - 1] if moving else times[0]
    return [((t - start) * 1000, dy / dp, dx / dp, c) for t, (c, dy, dx) in zip(times, res)]


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("video")
    p.add_argument("box", type=int, nargs=4)
    p.add_argument("--max-dy", type=int, default=0)
    p.add_argument("--max-dx", type=int, default=0)
    p.add_argument("--step", type=int, default=2, help="search step in px (refined to 1 around best)")
    p.add_argument("--dp", type=float, default=3.0, help="device pixels per dp of the recorded device")
    p.add_argument("--target", choices=["last", "first"], default="last")
    p.add_argument("--t0", type=float, default=0.0, help="ignore frames before (s, stream time)")
    p.add_argument("--t1", type=float, default=1e9, help="ignore frames after (s, stream time)")
    a = p.parse_args(argv)
    times, frames = read_gray_frames(a.video)
    for t_ms, dy, dx, c in displacement(times, frames, tuple(a.box), a.max_dy, a.max_dx, a.step, a.dp, a.target,
                                        a.t0, a.t1):
        print(f"{t_ms:8.1f}\t{dy:8.2f}\t{dx:8.2f}\t{c:6.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
