"""Screen geometry (Mutter DisplayConfig state) and cropping of a screenshot to one screen.

Pure helpers, no session access: the screenshot itself is taken by the nested Shell (Shell.Screenshot from a bench
extension), never by the xdg desktop portal of a real session. A capture driver writes <name>.png (the target
screen, see `crop`) and <name>-screen.json (see `screen_info`).
"""
from dataclasses import asdict, dataclass

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402


@dataclass
class Screen:
    name: str
    x: int          # logical px
    y: int
    width: float    # logical px
    height: float
    scale: float
    primary: bool


def screens_from(state):
    """Result of GetCurrentState -> logical screens (the "logical" layout mode of GNOME)."""
    _serial, monitors, logicals, _props = state.unpack()
    modes = {}
    for (connector, *_), modes_list, _p in monitors:
        for mode in modes_list:
            if mode[6].get("is-current"):
                modes[connector] = (mode[1], mode[2])
    out = []
    for x, y, scale, _transform, primary, specs, _p in logicals:
        connector = specs[0][0]
        w, h = modes[connector]
        out.append(Screen(connector, x, y, w / scale, h / scale, scale, primary))
    return out


def target_screen(screens):
    """Screen where to put the bench: the highest scale (the capture is rendered at that scale, its pixels are
    native there); on a tie, the primary screen."""
    return max(screens, key=lambda s: (round(s.scale, 3), s.primary))


def image_scale(screens, png_width):
    """Capture px per logical px."""
    return png_width / (max(s.x + s.width for s in screens) - min(s.x for s in screens))


def screen_area(screens, screen, png_width):
    """Rectangle (x, y, w, h) in capture px that corresponds to `screen`."""
    s = image_scale(screens, png_width)
    return (round(screen.x * s), round(screen.y * s), round(screen.width * s), round(screen.height * s))


def crop(png, screens, screen, destination):
    """Cut `screen` out of the capture; returns the scale of the image (px per logical px)."""
    pb = GdkPixbuf.Pixbuf.new_from_file(str(png))
    x, y, w, h = screen_area(screens, screen, pb.get_width())
    w, h = min(w, pb.get_width() - x), min(h, pb.get_height() - y)
    pb.new_subpixbuf(x, y, w, h).savev(str(destination), "png", [], [])
    return image_scale(screens, pb.get_width())


def screen_info(screens, screen, scale):
    """Content of <name>-screen.json, read by measure.py."""
    return {"screen": asdict(screen), "image_scale": scale, "screens": [asdict(s) for s in screens]}
