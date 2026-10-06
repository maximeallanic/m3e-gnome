"""Isolation guard of the bench: it opens full-screen GTK windows, so it may only run against the nested, headless
Shell started by nested.sh (named Wayland socket "m3e-bench-<pid>", private XDG_RUNTIME_DIR), never against a real
session."""
import re

NESTED_SOCKET = re.compile(r"m3e-bench-\d+")


def check_isolated(env):
    """None if `env` targets a nested bench Shell, otherwise the reason why the bench must not start."""
    display = env.get("WAYLAND_DISPLAY", "")
    if not NESTED_SOCKET.fullmatch(display):
        return (f"WAYLAND_DISPLAY={display!r} is not a nested bench socket (m3e-bench-<pid>): the bench opens "
                "full-screen windows and must never run in a real session")
    if env.get("DISPLAY"):
        return "DISPLAY is set: the bench must not be able to fall back to an X11 session"
    if env.get("GDK_BACKEND", "wayland") != "wayland":
        return f"GDK_BACKEND={env['GDK_BACKEND']!r}: the bench only runs on the nested Wayland socket"
    return None
