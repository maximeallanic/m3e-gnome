#!/usr/bin/env python3
"""Numbers on the smoothness of animations.mp4: frame timestamps (ffprobe) and the mean absolute difference between
consecutive frames (ffmpeg tblend + signalstats: luma average and maximum of the per-pixel difference, 0-255).
Run it on the lossless intermediate of mkvideo.py (--lossless) for exact duplicate detection: in the H.264 file the
encoder noise makes two identical pictures differ by a few levels, so a threshold (DUP) is used instead.

Usage: smoothness.py VIDEO [--csv FILE] [--exact]
Reports, for the "animated" frames (those inside a stretch of motion: a run of changing frames, at most HOLD frames of
stillness allowed inside it): the share of duplicated frames (difference below DUP), the largest time between two
distinct frames, and the timestamp deltas of the container (must be constant).
"""
import argparse
import re
import subprocess
import sys

DUP = 0.03      # mean luma difference under which two consecutive frames are the same picture (encoder noise level)
ACTIVE = 0.3    # mean luma difference above which a frame belongs to a visible motion (below: sub-pixel settling)
CUT = 60        # a mean luma difference above this is a cut between two scenes, not a motion
HOLD = 4        # frames of stillness tolerated inside a motion before it counts as two


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--csv")
    p.add_argument("--active", type=float, default=ACTIVE, help="luma difference marking a visible motion")
    p.add_argument("--gate", action="store_true",
                   help="exit 1 if a motion stretch has a gap over 40 ms or more than 20 %% duplicates (stretches of 6+ frames)")
    p.add_argument("--exact", action="store_true", help="lossless input: a duplicate is a frame with no changed pixel")
    a = p.parse_args()
    pts = [float(x.strip(",")) for x in run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "frame=pts_time",
                                  "-of", "csv=p=0", a.video]).stdout.split()]
    out = run(["ffmpeg", "-v", "error", "-i", a.video, "-vf",
               "format=gray,tblend=all_mode=difference,signalstats,metadata=print:file=-",
               "-f", "null", "-"]).stdout
    diff = [float(m) for m in re.findall(r"YAVG=([0-9.]+)", out)]
    ymax = [float(m) for m in re.findall(r"YMAX=([0-9.]+)", out)]
    n = min(len(pts), len(diff))
    pts, diff = pts[:n], diff[:n]
    moving = [m > 0 for m in ymax] if a.exact else [d > DUP for d in diff]
    active = [a.active < d < CUT for d in diff]
    active = [x and (active[i + 1] if i + 1 < n else False) or (x and i > 0 and active[i - 1]) for i, x in enumerate(active)]
    # motion stretches: first moving frame .. last moving frame, merged across gaps of <= HOLD still frames
    stretches, start, still = [], None, 0
    for i, m in enumerate(active):
        if m:
            if start is None:
                start = i
            last, still = i, 0
        elif start is not None:
            still += 1
            if still > HOLD:
                stretches.append((start, last))
                start = None
    if start is not None:
        stretches.append((start, last))
    stretches = [s for s in stretches if s[1] - s[0] >= 5]
    frames = [i for s, e in stretches for i in range(s, e + 1)]
    dup = [i for i in frames if not moving[i]]
    # time between distinct pictures inside the stretches
    gaps = []
    for s, e in stretches:
        prev = None
        for i in range(s, e + 1):
            if moving[i]:
                if prev is not None:
                    gaps.append((pts[i] - pts[prev]) * 1000)
                prev = i
    deltas = [(b - a) * 1000 for a, b in zip(pts, pts[1:])]
    print(f"frames {n}, container delta ms: min {min(deltas):.2f} max {max(deltas):.2f}")
    print(f"motion stretches: {len(stretches)}, frames inside: {len(frames)}")
    print(f"duplicated frames inside: {len(dup)} ({100 * len(dup) / max(1, len(frames)):.2f} %)")
    print(f"max gap between distinct pictures inside: {max(gaps):.1f} ms; gaps over 40 ms: {sum(g > 40 for g in gaps)}")
    for s, e in stretches:
        d = sum(1 for i in range(s, e + 1) if not moving[i])
        print(f"  {pts[s]:6.2f}-{pts[e]:6.2f} s  {e - s + 1:3d} frames  dup {d}")
    bad = []
    for s, e in stretches:
        d = sum(1 for i in range(s, e + 1) if not moving[i])
        pk = [i for i in range(s, e + 1) if moving[i]]
        worst = max([(pts[j] - pts[i]) * 1000 for i, j in zip(pk, pk[1:])] or [0])
        if worst > 40 or (e - s + 1 >= 8 and d > 0.2 * (e - s + 1)):
            bad.append(f"{pts[s]:.2f}-{pts[e]:.2f} s (dup {d}/{e - s + 1}, widest gap {worst:.0f} ms)")
    if bad:
        print("not smooth: " + "; ".join(bad))
    if a.csv:
        with open(a.csv, "w", encoding="utf-8") as f:
            f.writelines(f"{t:.4f},{d:.4f}\n" for t, d in zip(pts, diff))
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
