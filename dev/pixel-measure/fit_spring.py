#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Fit a damped spring to a measured displacement curve.

Input: TSV from displacement.py (t_ms, dy, dx, residual). Column COL (2 = dy, 3 = dx) is fitted with
x(t) = spring released at t_start from offset X0 toward 0, optional initial velocity V0, Compose units
(mass 1, stiffness = omega^2).
Prints dampingRatio, stiffness, t_start, X0, V0 and the RMS error in dp.

Usage: fit_spring.py TSV [--col 2] [--from-ms N] [--to-ms N] [--velocity]
"""
import argparse
import sys

import numpy as np


def spring(tt, zeta, k, x0, v0):
    """Position at times tt (s) of a unit-mass spring (stiffness k, damping ratio zeta) released at t = 0."""
    w = np.sqrt(k)
    tt = np.maximum(tt, 0)
    if zeta < 1:
        wd = w * np.sqrt(1 - zeta ** 2)
        return np.exp(-zeta * w * tt) * (x0 * np.cos(wd * tt) + (v0 + zeta * w * x0) / wd * np.sin(wd * tt))
    if zeta == 1:
        return np.exp(-w * tt) * (x0 + (v0 + w * x0) * tt)
    r1 = -w * (zeta - np.sqrt(zeta ** 2 - 1))
    r2 = -w * (zeta + np.sqrt(zeta ** 2 - 1))
    c2 = (v0 - r1 * x0) / (r2 - r1)
    c1 = x0 - c2
    return c1 * np.exp(r1 * tt) + c2 * np.exp(r2 * tt)


def fit(t, x, with_velocity=False):
    """Grid search on (zeta, stiffness, release time); X0 (and V0) enter linearly: least squares.
    Returns (rms, zeta, stiffness, t_start_s, X0[, V0])."""
    best = (1e18,)
    for zeta in np.r_[np.arange(0.3, 1.0, 0.025), 1.0, np.arange(1.05, 2.0, 0.05)]:
        for k in np.geomspace(30, 3000, 160):
            for ts in np.arange(t.min() - 0.12, t.min() + 0.06, 0.002):
                tt = t - ts
                basis = [spring(tt, zeta, k, 1.0, 0.0)]
                if with_velocity:
                    basis.append(spring(tt, zeta, k, 0.0, 1.0))
                basis = np.stack(basis, 1)
                basis[tt < 0] = 0
                before = tt < 0
                coef, *_ = np.linalg.lstsq(basis[~before], x[~before], rcond=None)
                model = basis @ coef
                model[before] = coef[0]  # before the release the element sits at X0
                err = float(np.sqrt(np.mean((model - x) ** 2)))
                if err < best[0]:
                    best = (err, zeta, k, ts, *coef)
    return best


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("tsv")
    p.add_argument("--col", type=int, default=2)
    p.add_argument("--from-ms", type=float, default=-1e9)
    p.add_argument("--to-ms", type=float, default=1e9)
    p.add_argument("--velocity", action="store_true", help="also fit an initial velocity")
    a = p.parse_args(argv)
    d = np.loadtxt(a.tsv)
    keep = (d[:, 0] >= a.from_ms) & (d[:, 0] <= a.to_ms)
    t, x = d[keep, 0] / 1000.0, d[keep, a.col - 1]
    err, zeta, k, ts, *coef = fit(t, x, a.velocity)
    print(f"dampingRatio={zeta:.3f} stiffness={k:.0f} t_start={ts * 1000:.0f}ms X0={coef[0]:.1f}dp"
          + (f" V0={coef[1]:.0f}dp/s" if a.velocity else "") + f" rms={err:.2f}dp")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
