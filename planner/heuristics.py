from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np

from utils.common import bilinear_interpolate


HeuristicFn = Callable[[float, float, float], float]


def euclidean_heuristic(goal_xy: Tuple[float, float]) -> HeuristicFn:
    gx, gy = goal_xy

    def _fn(x: float, y: float, yaw: float) -> float:
        del yaw
        return math.hypot(gx - x, gy - y)

    return _fn


@dataclass
class FieldHeuristic:
    field: np.ndarray
    resolution: float
    max_value: float = 1e6
    scale: float = 1.0

    def __call__(self, x: float, y: float, yaw: float) -> float:
        del yaw
        v = bilinear_interpolate(self.field, x, y, self.resolution)
        if not np.isfinite(v):
            return self.max_value
        v = float(np.clip(v, 0.0, self.max_value))
        return max(0.0, self.scale * v)


def compose_guidance(
    anchor_fn: HeuristicFn,
    guide_fn: Optional[HeuristicFn],
    blend: float,
) -> Callable[[float, float, float], Tuple[float, float]]:
    del blend

    def _fn(x: float, y: float, yaw: float) -> Tuple[float, float]:
        anchor = max(0.0, anchor_fn(x, y, yaw))
        if guide_fn is None:
            return anchor, anchor
        guide = max(0.0, guide_fn(x, y, yaw))
        return anchor, guide

    return _fn
