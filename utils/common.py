from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable

import numpy as np


try:
    import torch
except Exception:  # pragma: no cover
    torch = None


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)


def ensure_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def wrap_to_pi(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def bilinear_interpolate(field: np.ndarray, x: float, y: float, resolution: float) -> float:
    h, w = field.shape
    gx = x / resolution - 0.5
    gy = y / resolution - 0.5

    x0 = int(np.floor(gx))
    y0 = int(np.floor(gy))
    x1 = x0 + 1
    y1 = y0 + 1

    if x0 < 0 or y0 < 0 or x1 >= w or y1 >= h:
        xi = int(np.clip(round(gx), 0, w - 1))
        yi = int(np.clip(round(gy), 0, h - 1))
        return float(field[yi, xi])

    wx = gx - x0
    wy = gy - y0

    v00 = field[y0, x0]
    v10 = field[y0, x1]
    v01 = field[y1, x0]
    v11 = field[y1, x1]

    v0 = v00 * (1.0 - wx) + v10 * wx
    v1 = v01 * (1.0 - wx) + v11 * wx
    return float(v0 * (1.0 - wy) + v1 * wy)


def gaussian_2d(height: int, width: int, cx: float, cy: float, sigma: float) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width]
    return np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * sigma**2)).astype(np.float32)
