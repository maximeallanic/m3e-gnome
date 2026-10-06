#!/usr/bin/env python3
"""Print a deterministic description of a directory tree: one line per entry with type, mode, and the content hash
(files) or target (symlinks). Used to prove that uninstall leaves a home directory identical to its previous state."""
import hashlib
import os
import stat
import sys


def describe(root):
    lines = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(dirs + files):
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root)
            st = os.lstat(path)
            mode = stat.S_IMODE(st.st_mode)
            if stat.S_ISLNK(st.st_mode):
                lines.append(f"l {rel} -> {os.readlink(path)}")
            elif stat.S_ISDIR(st.st_mode):
                lines.append(f"d {mode:o} {rel}")
            else:
                digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
                lines.append(f"f {mode:o} {rel} {digest}")
    return lines


if __name__ == "__main__":
    print("\n".join(describe(sys.argv[1])))
