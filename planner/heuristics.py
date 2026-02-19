from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np

from env.dubins import shortest_path_length
from utils.common import bilinear_interpolate, trilinear_interpolate_yaw


HeuristicFn = Callable[[float, float, float], float]


def euclidean_heuristic(goal_xy: Tuple[float, float]) -> HeuristicFn:
    gx, gy = goal_xy

    def _fn(x: float, y: float, yaw: float) -> float:
        del yaw
        return math.hypot(gx - x, gy - y)

    return _fn


def dubins_heuristic(goal_pose: Tuple[float, float, float], min_turn_radius: float) -> HeuristicFn:
    def _fn(x: float, y: float, yaw: float) -> float:
        return shortest_path_length((x, y, yaw), goal_pose, rho=min_turn_radius)

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


@dataclass
class YawFieldHeuristic:
    field_3d: np.ndarray
    resolution: float
    max_value: float = 1e6
    scale: float = 1.0

    def __call__(self, x: float, y: float, yaw: float) -> float:
        v = trilinear_interpolate_yaw(self.field_3d, x, y, yaw, self.resolution)
        if not np.isfinite(v):
            return self.max_value
        v = float(np.clip(v, 0.0, self.max_value))
        return max(0.0, self.scale * v)


@dataclass
class ResidualYawFieldHeuristic:
    base_field_3d: np.ndarray
    residual_field_3d: np.ndarray
    resolution: float
    max_value: float = 1e6
    scale: float = 1.0

    def __call__(self, x: float, y: float, yaw: float) -> float:
        b = trilinear_interpolate_yaw(self.base_field_3d, x, y, yaw, self.resolution)
        r = trilinear_interpolate_yaw(self.residual_field_3d, x, y, yaw, self.resolution)
        v = b + r
        if not np.isfinite(v):
            return self.max_value
        v = float(np.clip(v, 0.0, self.max_value))
        return max(0.0, self.scale * v)


def compose_guidance(
    anchor_fn: HeuristicFn,
    guide_fn: Optional[HeuristicFn],
    blend: float,
) -> Callable[[float, float, float], Tuple[float, float]]:
    blend = float(np.clip(blend, 0.0, 1.0))

    def _fn(x: float, y: float, yaw: float) -> Tuple[float, float]:
        anchor = max(0.0, anchor_fn(x, y, yaw))
        if guide_fn is None:
            return anchor, anchor
        guide = max(0.0, guide_fn(x, y, yaw))
        guided = (1.0 - blend) * anchor + blend * guide
        return anchor, guided

    return _fn
