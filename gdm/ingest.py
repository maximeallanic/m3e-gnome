#!/usr/bin/python3 -I
"""Untrusted-data gate of the m3e-gnome GDM helper (Python standard library only).

The root helper never trusts what the user-side installer prepared. This program reads a directory as DATA, checks it,
and (for `ingest`) writes a clean copy into a root-owned staging directory. It never executes, imports or follows
anything from the input.

    ingest.py check  SRC          validate SRC, print nothing, exit 0 when acceptable
    ingest.py ingest SRC DST      validate SRC, write a clean copy to DST (DST must not exist)
    ingest.py hash   DIR          print "<sha256>  <relative path>" for every file of DIR, sorted

Layout accepted (anything else is refused):
    theme.css          required  UTF-8 Shell stylesheet, url() limited to an allow-list, no @import
    greeter.conf       required  key=value lines: icon_theme, cursor_theme, font_name, seed
    background.png     optional  PNG, magic + IHDR + IEND checked, dimensions bounded
    assets/icons/NAME/...   icon or cursor theme: regular files with allowed extensions only
    assets/fonts/NAME/...   fonts and licences

Rules for every entry: opened with O_NOFOLLOW relative to its parent directory descriptor, regular files and
directories only, no hard-linked files, not world-writable, size limits, names from a restricted alphabet.
"""
import hashlib
import os
import re
import stat
import struct
import sys
import zlib

# The helper directory was verified by m3e-gdm before this program runs; -I removes it from sys.path, so add it back.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import cssgate  # noqa: E402

MAX_CSS = 3 * 1024 * 1024
MAX_PNG = 24 * 1024 * 1024
MAX_PNG_SIDE = 8192
MAX_CONF = 4096
MAX_ASSET_FILE = 8 * 1024 * 1024
MAX_ASSET_TOTAL = 64 * 1024 * 1024
MAX_ASSET_FILES = 6000
MAX_DEPTH = 8
NAME_RE = re.compile(r"^[A-Za-z0-9_+,=@\[\]-][A-Za-z0-9 ._+,=@\[\]-]{0,127}$")
THEME_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EXT_ALLOWED = {".png", ".svg", ".ttf", ".otf", ".txt", ".theme"}
# Theme directories we may install: nothing that could shadow a system default (default, hicolor, Adwaita, ...).
ASSET_THEMES = {"icons": {"Material-Symbols", "Googlebook", "Googlebook-White"}, "fonts": {"GoogleSansFlex"}}
KEYS = ("icon_theme", "cursor_theme", "font_name", "seed")
VALUE_FORBIDDEN = re.compile(r"[\x00-\x1f\x7f'\"\\\[\]{}<>$`;|&]")


class Rejected(Exception):
    pass


def reject(msg):
    raise Rejected(msg)


def open_dir(path, dirfd=None):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        return os.open(path, flags, dir_fd=dirfd)
    except OSError as e:
        reject(f"cannot open directory {path!r} without following links: {e.strerror}")


def read_regular(name, dirfd, limit, shown):
    """Read a regular file through dirfd without following a link; refuse anything else."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dirfd)
    except OSError as e:
        reject(f"{shown}: cannot open (symbolic link?): {e.strerror}")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            reject(f"{shown}: not a regular file")
        if st.st_nlink > 1:
            reject(f"{shown}: hard-linked file")
        if st.st_mode & stat.S_IWOTH:
            reject(f"{shown}: world-writable")
        if st.st_size > limit:
            reject(f"{shown}: {st.st_size} bytes exceeds the limit of {limit}")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                reject(f"{shown}: grew beyond the limit of {limit} while reading")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def entry_kind(name, dirfd, shown):
    try:
        st = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    except OSError as e:
        reject(f"{shown}: {e.strerror}")
    if stat.S_ISLNK(st.st_mode):
        reject(f"{shown}: symbolic link")
    if st.st_mode & stat.S_IWOTH:
        reject(f"{shown}: world-writable")
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    if stat.S_ISREG(st.st_mode):
        return "file"
    reject(f"{shown}: neither a regular file nor a directory")


def check_name(name, shown):
    if not NAME_RE.match(name) or name in (".", "..") or ".." in name:
        reject(f"{shown}: file name outside the allowed alphabet")


def walk_assets(dirfd, rel, depth, tree, budget):
    if depth > MAX_DEPTH:
        reject(f"{rel}: nested too deeply")
    with os.scandir(dirfd) as it:
        names = sorted(e.name for e in it)
    for name in names:
        shown = f"{rel}/{name}"
        check_name(name, shown)
        kind = entry_kind(name, dirfd, shown)
        if kind == "dir":
            sub = open_dir(name, dirfd)
            try:
                walk_assets(sub, shown, depth + 1, tree, budget)
            finally:
                os.close(sub)
            continue
        budget["files"] += 1
        if budget["files"] > MAX_ASSET_FILES:
            reject("too many asset files")
        data = read_regular(name, dirfd, MAX_ASSET_FILE, shown)
        budget["bytes"] += len(data)
        if budget["bytes"] > MAX_ASSET_TOTAL:
            reject("assets exceed the total size limit")
        tree[shown] = data


def load_tree(src):
    """Return {relative path: bytes} for an input directory; raise Rejected on anything unexpected."""
    top = open_dir(src)
    tree = {}
    try:
        with os.scandir(top) as it:
            names = sorted(e.name for e in it)
        allowed = {"theme.css", "greeter.conf", "background.png", "assets"}
        for name in names:
            if name not in allowed:
                reject(f"unexpected entry: {name}")
            kind = entry_kind(name, top, name)
            if name == "assets":
                if kind != "dir":
                    reject("assets is not a directory")
                sub = open_dir(name, top)
                try:
                    walk_assets(sub, "assets", 1, tree, {"files": 0, "bytes": 0})
                finally:
                    os.close(sub)
            else:
                if kind != "file":
                    reject(f"{name} is not a regular file")
                limit = {"theme.css": MAX_CSS, "greeter.conf": MAX_CONF, "background.png": MAX_PNG}[name]
                tree[name] = read_regular(name, top, limit, name)
    finally:
        os.close(top)
    return tree


def validate_css(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        reject("theme.css: not valid UTF-8")
    try:
        cssgate.validate_css_text(text)
    except cssgate.CssRejected as e:
        reject(f"theme.css: {e}")


def validate_png(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        reject("background.png: not a PNG (bad magic)")
    if len(data) < 33 or data[12:16] != b"IHDR" or struct.unpack(">I", data[8:12])[0] != 13:
        reject("background.png: missing IHDR")
    if zlib.crc32(data[12:29]) & 0xFFFFFFFF != struct.unpack(">I", data[29:33])[0]:
        reject("background.png: IHDR checksum mismatch")
    width, height = struct.unpack(">II", data[16:24])
    if not (1 <= width <= MAX_PNG_SIDE and 1 <= height <= MAX_PNG_SIDE):
        reject(f"background.png: dimensions {width}x{height} outside 1..{MAX_PNG_SIDE}")
    if data[-12:] != b"\x00\x00\x00\x00IEND\xaeB`\x82":
        reject("background.png: truncated (no IEND chunk)")


def validate_conf(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        reject("greeter.conf: not valid UTF-8")
    seen = {}
    for n, line in enumerate(text.split("\n"), 1):
        if not line:
            continue
        key, sep, value = line.partition("=")
        if not sep or key not in KEYS or key in seen:
            reject(f"greeter.conf line {n}: unexpected or repeated key")
        if not value or len(value) > 80 or VALUE_FORBIDDEN.search(value):
            reject(f"greeter.conf line {n}: invalid value for {key}")
        if key in ("icon_theme", "cursor_theme") and not THEME_NAME_RE.match(value):
            reject(f"greeter.conf line {n}: {key} is not a plain theme name")
        seen[key] = value
    for key in ("icon_theme", "cursor_theme", "font_name"):
        if key not in seen:
            reject(f"greeter.conf: {key} missing")
    return seen


def validate_asset(path, data):
    parts = path.split("/")
    if len(parts) < 4 or parts[1] not in ("icons", "fonts"):
        reject(f"{path}: assets must be assets/icons/NAME/... or assets/fonts/NAME/...")
    if parts[2] not in ASSET_THEMES[parts[1]]:
        reject(f"{path}: theme directory {parts[2]!r} is not one of {sorted(ASSET_THEMES[parts[1]])}")
    ext = os.path.splitext(parts[-1])[1].lower()
    in_cursors = parts[1] == "icons" and len(parts) >= 5 and parts[3] == "cursors"
    if in_cursors:
        if data[:4] != b"Xcur":
            reject(f"{path}: not an Xcursor file")
        return
    if ext not in EXT_ALLOWED:
        reject(f"{path}: extension outside the allow-list")
    if ext == ".png":
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            reject(f"{path}: not a PNG")
    elif ext in (".ttf", ".otf"):
        if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
            reject(f"{path}: not a font file")
    elif ext in (".svg", ".txt", ".theme"):
        if b"\x00" in data:
            reject(f"{path}: NUL byte")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            reject(f"{path}: not valid UTF-8")
        if ext == ".svg" and re.search(r"href\s*=\s*[\"'](?!#|data:)", text, re.I):
            reject(f"{path}: external reference in SVG")


def validate(tree):
    for required in ("theme.css", "greeter.conf"):
        if required not in tree:
            reject(f"{required} missing")
    validate_css(tree["theme.css"])
    conf = validate_conf(tree["greeter.conf"])
    if "background.png" in tree:
        validate_png(tree["background.png"])
    for path, data in tree.items():
        if path.startswith("assets/"):
            validate_asset(path, data)
    return conf


def write_tree(tree, dst):
    os.mkdir(dst, 0o755)
    os.chmod(dst, 0o755)
    for path in sorted(tree):
        full = os.path.join(dst, path)
        os.makedirs(os.path.dirname(full), mode=0o755, exist_ok=True)
        fd = os.open(full, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "wb") as f:
            f.write(tree[path])
    for root, dirs, _files in os.walk(dst):
        os.chmod(root, 0o755)
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)


def digest_lines(tree):
    return [f"{hashlib.sha256(tree[p]).hexdigest()}  {p}" for p in sorted(tree)]


def main(argv):
    try:
        if len(argv) == 3 and argv[1] == "check":
            validate(load_tree(argv[2]))
        elif len(argv) == 4 and argv[1] == "ingest":
            if os.path.lexists(argv[3]):
                reject(f"destination exists: {argv[3]}")
            tree = load_tree(argv[2])
            validate(tree)
            write_tree(tree, argv[3])
        elif len(argv) == 4 and argv[1] == "strip-css":
            # User side: drop the comments of a rendered stylesheet so that the helper's checks see plain code.
            with open(argv[2], encoding="utf-8") as f:
                text = cssgate.strip_comments(f.read())
            with open(argv[3], "w", encoding="utf-8") as f:
                f.write(text)
        elif len(argv) == 3 and argv[1] == "hash":
            print("\n".join(digest_lines(load_tree(argv[2]))))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (Rejected, cssgate.CssRejected) as e:
        print(f"ingest: refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
