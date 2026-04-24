from __future__ import annotations

import math
from typing import Tuple

import numpy as np


def mod2pi(theta: np.ndarray | float) -> np.ndarray | float:
    two_pi = 2.0 * np.pi
    return theta - two_pi * np.floor(theta / two_pi)


def _lsl(alpha: np.ndarray, beta: np.ndarray, d: np.ndarray) -> np.ndarray:
    tmp0 = d + np.sin(alpha) - np.sin(beta)
    p2 = 2.0 + d * d - 2.0 * np.cos(alpha - beta) + 2.0 * d * (np.sin(alpha) - np.sin(beta))
    valid = p2 >= 0.0
    p = np.sqrt(np.clip(p2, 0.0, None))
    tmp1 = np.arctan2(np.cos(beta) - np.cos(alpha), tmp0)
    t = mod2pi(-alpha + tmp1)
    q = mod2pi(beta - tmp1)
    out = t + p + q
    out = np.where(valid, out, np.inf)
    return out


def _rsr(alpha: np.ndarray, beta: np.ndarray, d: np.ndarray) -> np.ndarray:
    tmp0 = d - np.sin(alpha) + np.sin(beta)
    p2 = 2.0 + d * d - 2.0 * np.cos(alpha - beta) + 2.0 * d * (np.sin(beta) - np.sin(alpha))
    valid = p2 >= 0.0
    p = np.sqrt(np.clip(p2, 0.0, None))
    tmp1 = np.arctan2(np.cos(alpha) - np.cos(beta), tmp0)
    t = mod2pi(alpha - tmp1)
    q = mod2pi(-beta + tmp1)
    out = t + p + q
    out = np.where(valid, out, np.inf)
    return out


def _lsr(alpha: np.ndarray, beta: np.ndarray, d: np.ndarray) -> np.ndarray:
    p2 = -2.0 + d * d + 2.0 * np.cos(alpha - beta) + 2.0 * d * (np.sin(alpha) + np.sin(beta))
    valid = p2 >= 0.0
    p = np.sqrt(np.clip(p2, 0.0, None))
    tmp2 = np.arctan2(-np.cos(alpha) - np.cos(beta), d + np.sin(alpha) + np.sin(beta)) - np.arctan2(-2.0, p)
    t = mod2pi(-alpha + tmp2)
    q = mod2pi(-beta + tmp2)
    out = t + p + q
    out = np.where(valid, out, np.inf)
    return out


def _rsl(alpha: np.ndarray, beta: np.ndarray, d: np.ndarray) -> np.ndarray:
    p2 = -2.0 + d * d + 2.0 * np.cos(alpha - beta) - 2.0 * d * (np.sin(alpha) + np.sin(beta))
    valid = p2 >= 0.0
    p = np.sqrt(np.clip(p2, 0.0, None))
    tmp2 = np.arctan2(np.cos(alpha) + np.cos(beta), d - np.sin(alpha) - np.sin(beta)) - np.arctan2(2.0, p)
    t = mod2pi(alpha - tmp2)
    q = mod2pi(beta - tmp2)
    out = t + p + q
    out = np.where(valid, out, np.inf)
    return out


def _rlr(alpha: np.ndarray, beta: np.ndarray, d: np.ndarray) -> np.ndarray:
    tmp = (6.0 - d * d + 2.0 * np.cos(alpha - beta) + 2.0 * d * (np.sin(alpha) - np.sin(beta))) / 8.0
    valid = np.abs(tmp) <= 1.0
    p = mod2pi(2.0 * np.pi - np.arccos(np.clip(tmp, -1.0, 1.0)))
    t = mod2pi(alpha - np.arctan2(np.cos(alpha) - np.cos(beta), d - np.sin(alpha) + np.sin(beta)) + 0.5 * p)
    q = mod2pi(alpha - beta - t + p)
    out = t + p + q
    out = np.where(valid, out, np.inf)
    return out


def _lrl(alpha: np.ndarray, beta: np.ndarray, d: np.ndarray) -> np.ndarray:
    tmp = (6.0 - d * d + 2.0 * np.cos(alpha - beta) + 2.0 * d * (-np.sin(alpha) + np.sin(beta))) / 8.0
    valid = np.abs(tmp) <= 1.0
    p = mod2pi(2.0 * np.pi - np.arccos(np.clip(tmp, -1.0, 1.0)))
    t = mod2pi(-alpha - np.arctan2(np.cos(alpha) - np.cos(beta), d + np.sin(alpha) - np.sin(beta)) + 0.5 * p)
    q = mod2pi(beta - alpha - t + p)
    out = t + p + q
    out = np.where(valid, out, np.inf)
    return out


def shortest_path_length(start: Tuple[float, float, float], goal: Tuple[float, float, float], rho: float) -> float:
    x0, y0, yaw0 = start
    x1, y1, yaw1 = goal

    dx = x1 - x0
    dy = y1 - y0
    D = math.hypot(dx, dy)
    d = D / max(rho, 1e-6)

    theta = math.atan2(dy, dx)
    alpha = float(mod2pi(yaw0 - theta))
    beta = float(mod2pi(yaw1 - theta))

    A = np.array(alpha, dtype=np.float64)
    B = np.array(beta, dtype=np.float64)
    DD = np.array(d, dtype=np.float64)

    candidates = [
        _lsl(A, B, DD),
        _rsr(A, B, DD),
        _lsr(A, B, DD),
        _rsl(A, B, DD),
        _rlr(A, B, DD),
        _lrl(A, B, DD),
    ]
    best = float(np.min(np.asarray(candidates)))
    if not np.isfinite(best):
        return float("inf")
    return best * rho


def yaw_bin_centers(num_bins: int) -> np.ndarray:
    step = 2.0 * np.pi / max(num_bins, 1)
    return ((np.arange(num_bins, dtype=np.float32) + 0.5) * step - np.pi).astype(np.float32)


def compute_dubins_field(
    occupancy: np.ndarray,
    goal: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    rho: float,
    fill_value: float,
) -> np.ndarray:
    """3D Dubins lower-bound field [yaw_bin, y, x]. Obstacle cells are set to fill_value."""
    h, w = occupancy.shape
    yy, xx = np.mgrid[0:h, 0:w]
    wx = (xx + 0.5) * resolution
    wy = (yy + 0.5) * resolution

    gx, gy, gyaw = goal
    dx = gx - wx
    dy = gy - wy
    D = np.hypot(dx, dy)
    d = D / max(rho, 1e-6)
    theta = np.arctan2(dy, dx)

    out = np.empty((yaw_bins, h, w), dtype=np.float32)
    yaw_centers = yaw_bin_centers(yaw_bins)

    beta = mod2pi(gyaw - theta)
    for k, yaw0 in enumerate(yaw_centers):
        alpha = mod2pi(yaw0 - theta)

        lengths = np.stack(
            [
                _lsl(alpha, beta, d),
                _rsr(alpha, beta, d),
                _lsr(alpha, beta, d),
                _rsl(alpha, beta, d),
                _rlr(alpha, beta, d),
                _lrl(alpha, beta, d),
            ],
            axis=0,
        )
        best = np.min(lengths, axis=0) * rho
        best[~np.isfinite(best)] = fill_value
        best = np.where(occupancy, fill_value, best)
        out[k] = best.astype(np.float32)

    return out
