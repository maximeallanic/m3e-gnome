"""Expected rows of the Shell style bench: one `grid.Row` per measured element (same shape as dev/m3e-bench/grid.py,
see its docstring). Every row has `toolkits={"shell"}`.

`batch` is the work batch that introduced the row; the witness rows (id `witness-...`) are measured in every batch.
`SURFACE` maps a row id to the surface of surfaces.js (bench extension m3e-bench-style) that captures it.

Modules, by concern: base_top_bar, menus, quick_settings, quick_settings_menu, calendar, notifications, overview,
dialogs, screenshot_keyboard, lock_login. Row order is the order of the report and of the surfaces of a batch.

Command line (used by run.sh): `python3 -m expected [batch]` prints the comma-separated surfaces of a batch (all
without a batch); `python3 -m expected --gdm` prints the surfaces played in the gdm-mode nested Shell.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3e-bench"))
from grid import STATES, Row  # noqa: E402,F401

from . import (base_top_bar, calendar, dialogs, lock_login, menus, notifications, overview,  # noqa: E402
               quick_settings, quick_settings_menu, screenshot_keyboard)

_MODULES = [base_top_bar, menus, quick_settings, quick_settings_menu, calendar, notifications, overview, dialogs,
            screenshot_keyboard, lock_login]

ROWS = [row for module in _MODULES for row in module.ROWS]
SURFACE = {row_id: surface for module in _MODULES for row_id, surface in module.SURFACE.items()}
SURFACES_GDM = lock_login.SURFACES_GDM


def surfaces_for(batch=None):
    """Surfaces to capture: those of the rows of the batch plus those of the witnesses; without a batch, all (row order)."""
    names = []
    for row in ROWS:
        if batch is None or row.batch == batch or row.id.startswith("witness-"):
            surface = SURFACE[row.id]
            if surface not in names:
                names.append(surface)
    return names
