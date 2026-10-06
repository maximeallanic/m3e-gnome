"""Row constructor shared by the expected-row modules of the Shell bench."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3e-bench"))
from grid import STATES, Row  # noqa: E402,F401


def shell_row(row_id, batch, states, expected, **measure):
    """A row measured in the Shell only (`toolkits={"shell"}`). `measure`: options of the measurement (grid.Row)."""
    return Row(row_id, batch, toolkits={"shell"}, states=list(states), expected=expected, measure=measure)
