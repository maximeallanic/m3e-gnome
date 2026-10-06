#!/usr/bin/env bash
# Creates dev/screenshots/.venv (git-ignored): system site packages (PyGObject, dbus-python) + python-dbusmock and
# Pillow. python-dbusmock is installed without its dbus-python dependency (it would be compiled from source; the
# distribution's python3-dbus is used instead).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v uv >/dev/null || { echo "uv is required (https://docs.astral.sh/uv/)" >&2; exit 1; }
python3 -c 'import dbus, gi' 2>/dev/null || { echo "python3-dbus and python3-gi (PyGObject) are required" >&2; exit 1; }
uv venv --system-site-packages --quiet "$HERE/.venv"
VIRTUAL_ENV="$HERE/.venv" uv pip install --quiet --no-deps python-dbusmock
VIRTUAL_ENV="$HERE/.venv" uv pip install --quiet pillow
echo "ready: $HERE/.venv"
