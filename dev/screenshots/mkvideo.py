#!/usr/bin/env python3
"""Retime and cut the slow-motion recordings of video.py into the final video, and derive the WebP and the poster frame.

Usage: mkvideo.py --dark DIR --light DIR --out DIR [--duration 15.0] [--fps 60] [--crf 20] [--width 1920]
  --dark / --light  capture.sh output directories holding <mode>/marks-<mode>.json and the raw recording next to it
  --out             destination: animations.mp4, animations.webp, animations-poster.png
The recordings are made with the Shell's animation clock slowed by marks["slowdown"] (video.py) and are
variable-frame-rate (one frame per change of the screen). Each scene interval is cut by timestamp, its timestamps are divided
by the slow-down factor (so every animation has its real duration) and the result is made constant-rate with ffmpeg's `fps`
filter, which keeps, for every output instant, the NEAREST captured frame (no blending, no interpolation). With the factor
at 4 the capture has several frames per output frame, so frames are only dropped, never repeated.
Scenes are joined with plain cuts; a small caption names each one.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CAPTIONS = {
    "overview": "Overview and app grid", "window": "Window open and close", "quick-settings": "Quick Settings: tile morph",
    "switch": "Popup menu and switch", "notifications": "Notifications", "alt-tab": "Alt+Tab",
}
LIGHT_CAPTION = "Light palette"
# Frames dropped at the start of each scene (the recording clock is read just before the first action).
PAD = 0.0


def segments(args):
    out = []
    for mode, directory in (("dark", args.dark), ("light", args.light)):
        marks = json.loads((Path(directory) / mode / f"marks-{mode}.json").read_text(encoding="utf-8"))
        raw = Path(directory) / mode / marks["file"]
        for scene in marks["scenes"]:
            caption = LIGHT_CAPTION if mode == "light" else CAPTIONS[scene["name"]]
            out.append({"raw": raw, "start": scene["start"] + args.offset + PAD, "end": scene["end"] + args.offset,
                        "caption": caption, "mode": mode, "slow": scene.get("slow", marks.get("slowdown", 1)), "scene": scene["name"], **args.trim.get((mode, scene["name"]), {})})
    return out


def fit(segs, duration, max_cut=0.4):
    """Brings the total to `duration`: the excess is taken from the tails of the scenes (the idle moment after the last
    motion), at most `max_cut` seconds from each, the longest tails first. Raises if that is not enough."""
    length = lambda s: (s["end"] - s["start"]) / s["slow"]       # seconds of animation time
    excess = sum(length(s) for s in segs) - duration
    for s in sorted(segs, key=length, reverse=True):
        if excess <= 0:
            break
        cut = min(max_cut, excess)
        s["end"] -= cut * s["slow"]
        excess -= cut
    if excess > 0.01:
        raise SystemExit(f"mkvideo: {excess:.2f} s too long even after trimming every tail: shorten the scenes in video.py")
    if excess < -0.25:
        print(f"mkvideo: {-excess:.2f} s shorter than {duration} s: the last frame is held", file=sys.stderr)


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dark", required=True)
    p.add_argument("--light", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--duration", type=float, default=15.0)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--crf", type=int, default=20)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--lossless", help="also write the retimed frames, before the H.264 encode, as FFV1 (smoothness.py --exact)")
    p.add_argument("--offset", type=float, default=0.0, help="seconds added to every mark (recording clock skew)")
    p.add_argument("--trim", default="{}", help='JSON {"mode/scene": {"start_shift": s, "end_shift": s}} adjustments in seconds')
    args = p.parse_args()
    args.trim = {tuple(k.split("/")): v for k, v in json.loads(args.trim).items()}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    segs = segments(args)
    inputs, graph, labels, total = [], [], [], 0.0
    for sg in segs:
        sg["start"] += sg.pop("start_shift", 0.0)
        sg["end"] += sg.pop("end_shift", 0.0)
    fit(segs, args.duration)
    files = sorted({s["raw"] for s in segs})
    for f in files:
        inputs += ["-i", str(f)]
    height = round(args.width * 9 / 16 / 2) * 2
    for i, s in enumerate(segs):
        idx = files.index(s["raw"])
        caption = s["caption"].replace(":", r"\:")
        graph.append(
            f"[{idx}:v]trim=start={s['start']:.3f}:end={s['end']:.3f},setpts=(PTS-STARTPTS)/{s['slow']},fps={args.fps}:round=near,"
            f"scale={args.width}:{height}:flags=lanczos,"
            f"drawtext=fontfile={FONT}:text='{caption}':fontsize={round(args.width * 0.021)}:fontcolor=white:"
            f"box=1:boxcolor=black@0.55:boxborderw={round(args.width * 0.008)}:x=(w-text_w)/2:y=h-{round(args.width * 0.05)}[v{i}]")
        labels.append(f"[v{i}]")
        total += (s["end"] - s["start"]) / s["slow"]
    graph.append("".join(labels) + f"concat=n={len(segs)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=1[out]")
    print(f"scenes: {len(segs)}, total {total:.2f} s (target {args.duration})", file=sys.stderr)
    mp4 = out / "animations.mp4"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[out]", "-t", str(args.duration),
         "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-pix_fmt", "yuv420p", "-r", str(args.fps),
         "-movflags", "+faststart", "-an", str(mp4)])
    if args.lossless:
        run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[out]", "-t",
             str(args.duration), "-c:v", "ffv1", "-an", args.lossless])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", "fps=50,scale=800:-1:flags=lanczos", "-c:v", "libwebp_anim",
         "-quality", "60", "-compression_level", "6", "-loop", "0", str(out / "animations.webp")])
    run(["ffmpeg", "-v", "error", "-y", "-ss", "1.0", "-i", str(mp4), "-frames:v", "1", str(out / "animations-poster.png")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
