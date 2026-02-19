from __future__ import annotations

import heapq
from typing import Tuple

import numpy as np

from config import PlannerConfig, VehicleConfig
from env.dubins import compute_dubins_field
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field


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


def _esdf_obstacle_cost(esdf: np.ndarray | None, threshold_m: float) -> np.ndarray | None:
    if esdf is None:
        return None
    d = np.maximum(esdf.astype(np.float32), 0.0)
    threshold = float(max(threshold_m, 1e-3))
    return np.maximum(0.0, threshold - d).astype(np.float32)


def compute_nonholonomic_teacher(
    occupancy: np.ndarray,
    goal_pose: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    min_turn_radius: float,
    fill_value: float,
    teacher_mode: str = "dubins_proxy",
    esdf: np.ndarray | None = None,
    hybrid_obstacle_alpha: float = 0.0,
    hybrid_obstacle_threshold_m: float = 1.5,
    rs_backend: str = "auto",
    rs_step_size: float = 1.0,
    planner_cfg: PlannerConfig | None = None,
    vehicle_cfg: VehicleConfig | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns:
      teacher_2d: [H, W] obstacle-aware holonomic field.
      teacher_3d: [yaw_bin, H, W] nonholonomic field.
    """
    teacher_2d = compute_2d_dijkstra_field(occupancy, (goal_pose[0], goal_pose[1]), resolution)
    teacher_2d = fill_unreachable(teacher_2d, occupancy, fill_value=fill_value)

    mode = str(teacher_mode).lower()
    if mode in {"dubins", "dubins_only"}:
        teacher_3d = compute_dubins_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
        )
    elif mode in {"dubins_proxy", "dubins_distilled"}:
        dubins_3d = compute_dubins_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
        )

        h, w = occupancy.shape
        yy, xx = np.mgrid[0:h, 0:w]
        wx = (xx + 0.5) * resolution
        wy = (yy + 0.5) * resolution
        to_goal = np.arctan2(goal_pose[1] - wy, goal_pose[0] - wx)

        # Suppress heading penalty near goal to align with finite goal tolerances in planner.
        dist_gate = np.tanh(np.maximum(teacher_2d, 0.0) / max(2.0 * min_turn_radius, 1e-3))

        yaw_centers = ((np.arange(yaw_bins, dtype=np.float32) + 0.5) * (2.0 * np.pi / yaw_bins) - np.pi).astype(np.float32)
        proxy = np.empty_like(dubins_3d, dtype=np.float32)
        for k, yaw0 in enumerate(yaw_centers):
            d1 = np.abs((yaw0 - to_goal + np.pi) % (2.0 * np.pi) - np.pi)
            d2 = np.abs((goal_pose[2] - to_goal + np.pi) % (2.0 * np.pi) - np.pi)
            turn_cost = min_turn_radius * (d1 + 0.5 * d2) * dist_gate
            proxy[k] = (teacher_2d + turn_cost).astype(np.float32)

        teacher_3d = np.minimum(dubins_3d, proxy)
    elif mode in {"reeds_shepp", "rs"}:
        teacher_3d = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
            step_size=rs_step_size,
            backend=rs_backend,
            cost_mode="length",
        )
    elif mode in {"reeds_shepp_consistent", "rs_consistent", "reeds_shepp_costaware"}:
        if planner_cfg is None or vehicle_cfg is None:
            raise ValueError("planner_cfg and vehicle_cfg are required for reeds_shepp_consistent mode")
        cost_cfg = RSConsistentCostConfig.from_configs(vehicle_cfg=vehicle_cfg, planner_cfg=planner_cfg)
        teacher_3d = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
            step_size=rs_step_size,
            backend=rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=cost_cfg,
        )
    elif mode in {"hybrid_rs_esdf", "hybrid", "rs_hybrid"}:
        teacher_rs = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
            step_size=rs_step_size,
            backend=rs_backend,
            cost_mode="length",
        )
        cost = _esdf_obstacle_cost(esdf, threshold_m=hybrid_obstacle_threshold_m)
        if cost is None:
            teacher_3d = teacher_rs
        else:
            teacher_3d = (teacher_rs + float(hybrid_obstacle_alpha) * cost[None, ...]).astype(np.float32)
    elif mode in {"hybrid_rs_consistent_esdf", "hybrid_consistent", "rs_consistent_hybrid"}:
        if planner_cfg is None or vehicle_cfg is None:
            raise ValueError("planner_cfg and vehicle_cfg are required for hybrid_rs_consistent_esdf mode")
        cost_cfg = RSConsistentCostConfig.from_configs(vehicle_cfg=vehicle_cfg, planner_cfg=planner_cfg)
        teacher_rs = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
            step_size=rs_step_size,
            backend=rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=cost_cfg,
        )
        cost = _esdf_obstacle_cost(esdf, threshold_m=hybrid_obstacle_threshold_m)
        if cost is None:
            teacher_3d = teacher_rs
        else:
            teacher_3d = (teacher_rs + float(hybrid_obstacle_alpha) * cost[None, ...]).astype(np.float32)
    else:
        raise ValueError(f"Unknown teacher_mode: {teacher_mode}")

    teacher_3d[:, occupancy] = fill_value
    teacher_3d = np.where(np.isfinite(teacher_3d), teacher_3d, fill_value).astype(np.float32)
    return teacher_2d.astype(np.float32), teacher_3d
