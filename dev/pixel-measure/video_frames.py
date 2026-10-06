"""Frame extraction shared by the screen-recording measurement tools (needs ffmpeg and ffprobe on PATH)."""
import subprocess

import numpy as np


def probe(video, entries):
    """ffprobe `-show_entries <entries>` of the video stream, one value per list item. The `default` writer is used
    because `csv` appends a trailing comma to frame entries on current ffprobe versions."""
    return subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", entries,
         "-of", "default=noprint_wrappers=1:nokey=1", video], text=True).split()


def read_gray_frames(video):
    """Return (times_s, frames) of a video: frames is a (n, height, width) uint8 array, one entry per decoded
    frame (variable frame rate kept: no resampling), times_s the presentation time of each frame."""
    width, height = map(int, probe(video, "stream=width,height")[:2])
    times = np.array([float(t) for t in probe(video, "frame=pts_time")])
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        stdout=subprocess.PIPE, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, height, width)[:len(times)]
    return times, frames
