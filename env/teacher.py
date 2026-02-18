from __future__ import annotations

import heapq
from typing import Tuple

import numpy as np


def world_to_grid(x: float, y: float, resolution: float) -> Tuple[int, int]:
    gx = int(np.clip(np.floor(x / resolution), 0, np.iinfo(np.int32).max))
    gy = int(np.clip(np.floor(y / resolution), 0, np.iinfo(np.int32).max))
    return gx, gy


def compute_2d_dijkstra_field(
    occupancy: np.ndarray,
    goal_xy: Tuple[float, float],
    resolution: float,
) -> np.ndarray:
    """Return distance-to-goal for every grid cell (meters); inf for obstacles/unreachable."""
    h, w = occupancy.shape
    gx, gy = world_to_grid(goal_xy[0], goal_xy[1], resolution)
    gx = int(np.clip(gx, 0, w - 1))
    gy = int(np.clip(gy, 0, h - 1))

    dist = np.full((h, w), np.inf, dtype=np.float32)
    if occupancy[gy, gx]:
        return dist

    neighbors = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, np.sqrt(2.0)),
        (-1, 1, np.sqrt(2.0)),
        (1, -1, np.sqrt(2.0)),
        (1, 1, np.sqrt(2.0)),
    ]

    pq = [(0.0, gy, gx)]
    dist[gy, gx] = 0.0

    while pq:
        cur_d, y, x = heapq.heappop(pq)
        if cur_d > float(dist[y, x]):
            continue

        for dx, dy, step in neighbors:
            nx = x + dx
            ny = y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue

            nd = cur_d + step * resolution
            if nd < float(dist[ny, nx]):
                dist[ny, nx] = nd
                heapq.heappush(pq, (nd, ny, nx))

    return dist


def fill_unreachable(
    field: np.ndarray,
    occupancy: np.ndarray,
    fill_value: float,
) -> np.ndarray:
    result = field.copy()
    unreachable = ~np.isfinite(result)
    result[unreachable] = fill_value
    result[occupancy] = fill_value
    return result.astype(np.float32)
