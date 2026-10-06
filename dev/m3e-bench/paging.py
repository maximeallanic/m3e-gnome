"""Layout and paging of the bench grid, with no GTK: which rows go on a page, how much fits on the screen, the
measurement area of overlays, and the layout document that measure.py reads. Pure functions, unit-tested."""
import grid

MARGIN = 12            # logical px around the target (focus ring included)
CELL = (176, 80)       # logical px (6 columns must fit in 1692 px, the width of a 1.33-scaled laptop screen)
BOTTOM_GAP = 8         # logical px kept free under the last row of a page

# Overlays: measurement area (logical px, relative to the window) computed from the bounds of the target
# (x, y, w, h) and the window size (window_w, window_h).
ZONES = {
    "menu": lambda x, y, w, h, window_w, window_h: (x - 60, y + h, 380, 300),
    "dialog": lambda x, y, w, h, window_w, window_h: (window_w / 2 - 330, window_h / 2 - 220, 660, 440),
}


def page_name(toolkit, batch, page):
    return f"{toolkit}-b{batch}-p{page}"


def select_rows(toolkit, batch, wanted=None):
    """(rows of this page, ids of dialog rows deferred to a later page).

    `wanted` = ids requested for this page (the witness is always there). The dialog is modal and centred: alone
    on its page, without the witness that the dialog scrim would darken."""
    rows = grid.rows_for(toolkit, batch)
    if wanted:
        rows = [r for r in rows if r.batch == 1 or r.id in wanted]
    if any(r.id == "dialog" for r in rows):
        others = [r for r in rows if r.id not in ("dialog", "header")]
        rows = [r for r in rows if r.id == "dialog"] if not others else [r for r in rows if r.id != "dialog"]
    placed = {r.id for r in rows}
    deferred = [r.id for r in grid.rows_for(toolkit, batch)
                if r.id == "dialog" and (not wanted or r.id in wanted) and r.id not in placed]
    return rows, deferred


def fit_rows(bounds, window_height):
    """Ids of the rows that do not fit on the page. `bounds` = [(row id, y, height)] in display order; the header
    witness never moves; once a row overflows, every following row is deferred too (rows stay in order)."""
    remaining = []
    for rid, y, h in bounds:
        if rid == "header":
            continue
        if remaining or y + h > window_height - BOTTOM_GAP:
            remaining.append(rid)
    return remaining


def cell_record(row_id, state, bounds, window_size):
    """Layout cell of a placed widget: the measurement area around `bounds` (x, y, w, h)."""
    x, y, w, h = bounds
    if row_id in ZONES:
        zx, zy, zw, zh = ZONES[row_id](x, y, w, h, *window_size)
        return {"row": row_id, "state": state, "x": zx, "y": zy, "w": zw, "h": zh}
    return {"row": row_id, "state": state, "x": x - MARGIN, "y": y - MARGIN,
            "w": w + 2 * MARGIN, "h": h + 2 * MARGIN}


def layout_document(toolkit, batch, page, window, screen, logical_screen, remaining, cells):
    """Content of layout-<name>.json (see measure.py)."""
    return {"toolkit": toolkit, "batch": batch, "page": page, "window": list(window), "screen": screen,
            "logical_screen": list(logical_screen), "ignored_inputs": True, "remaining": remaining,
            "cells": cells}
