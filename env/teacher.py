from __future__ import annotations

import heapq
import math
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


def _draw_disk_bool(mask: np.ndarray, cx: int, cy: int, r: int) -> None:
    h, w = mask.shape
    x0 = max(0, cx - r)
    x1 = min(w - 1, cx + r)
    y0 = max(0, cy - r)
    y1 = min(h - 1, cy + r)
    if x0 > x1 or y0 > y1:
        return
    yy, xx = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
    local = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    mask[y0 : y1 + 1, x0 : x1 + 1] |= local


def _dynamic_occupancy_at_step(
    shape: tuple[int, int],
    dynamic_tracks: np.ndarray | None,
    dynamic_radii_m: np.ndarray | None,
    resolution: float,
    step_idx: int,
) -> np.ndarray:
    h, w = shape
    if dynamic_tracks is None or dynamic_tracks.size == 0:
        return np.zeros((h, w), dtype=bool)
    if dynamic_tracks.ndim != 3 or dynamic_tracks.shape[-1] != 2:
        return np.zeros((h, w), dtype=bool)
    if step_idx < 0 or step_idx >= dynamic_tracks.shape[1]:
        return np.zeros((h, w), dtype=bool)

    if dynamic_radii_m is None or dynamic_radii_m.size == 0:
        radii_m = np.full((dynamic_tracks.shape[0],), resolution, dtype=np.float32)
    else:
        radii_m = np.asarray(dynamic_radii_m, dtype=np.float32).reshape(-1)
        if radii_m.shape[0] < dynamic_tracks.shape[0]:
            pad = np.full((dynamic_tracks.shape[0] - radii_m.shape[0],), float(np.mean(radii_m)) if radii_m.size > 0 else resolution, dtype=np.float32)
            radii_m = np.concatenate([radii_m, pad], axis=0)

    dyn = np.zeros((h, w), dtype=bool)
    for i in range(dynamic_tracks.shape[0]):
        x = float(dynamic_tracks[i, step_idx, 0])
        y = float(dynamic_tracks[i, step_idx, 1])
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        gx = int(np.clip(np.floor(x / resolution), 0, w - 1))
        gy = int(np.clip(np.floor(y / resolution), 0, h - 1))
        r_cells = int(max(1, math.ceil(float(radii_m[i]) / max(resolution, 1e-6))))
        _draw_disk_bool(dyn, gx, gy, r_cells)
    return dyn


def _compute_teacher_3d_core(
    occupancy: np.ndarray,
    goal_pose: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    min_turn_radius: float,
    fill_value: float,
    mode: str,
    teacher_2d: np.ndarray,
    esdf: np.ndarray | None,
    hybrid_obstacle_alpha: float,
    hybrid_obstacle_threshold_m: float,
    rs_backend: str,
    rs_step_size: float,
    planner_cfg: PlannerConfig | None,
    vehicle_cfg: VehicleConfig | None,
) -> np.ndarray:
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
        raise ValueError(f"Unknown teacher_mode: {mode}")

    teacher_3d[:, occupancy] = fill_value
    teacher_3d = np.where(np.isfinite(teacher_3d), teacher_3d, fill_value).astype(np.float32)
    return teacher_3d


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
    return_temporal_residual: bool = False,
    temporal_indices: tuple[int, ...] = (0, 1, 2),
    dynamic_tracks: np.ndarray | None = None,
    dynamic_radii_m: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
      teacher_2d: [H, W] obstacle-aware holonomic field.
      teacher_3d: [yaw_bin, H, W] nonholonomic field.
    """
    teacher_2d = compute_2d_dijkstra_field(occupancy, (goal_pose[0], goal_pose[1]), resolution)
    teacher_2d = fill_unreachable(teacher_2d, occupancy, fill_value=fill_value)

    mode = str(teacher_mode).lower()
    teacher_3d = _compute_teacher_3d_core(
        occupancy=occupancy,
        goal_pose=goal_pose,
        resolution=resolution,
        yaw_bins=yaw_bins,
        min_turn_radius=min_turn_radius,
        fill_value=fill_value,
        mode=mode,
        teacher_2d=teacher_2d,
        esdf=esdf,
        hybrid_obstacle_alpha=hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=hybrid_obstacle_threshold_m,
        rs_backend=rs_backend,
        rs_step_size=rs_step_size,
        planner_cfg=planner_cfg,
        vehicle_cfg=vehicle_cfg,
    )
    if not return_temporal_residual:
        return teacher_2d.astype(np.float32), teacher_3d

    if planner_cfg is not None and vehicle_cfg is not None:
        base_cfg = RSConsistentCostConfig.from_configs(vehicle_cfg=vehicle_cfg, planner_cfg=planner_cfg)
        rs_base = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=min_turn_radius,
            fill_value=fill_value,
            step_size=rs_step_size,
            backend=rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=base_cfg,
        )
    else:
        rs_base = compute_reeds_shepp_field(
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
    rs_base[:, occupancy] = fill_value
    rs_base = np.where(np.isfinite(rs_base), rs_base, fill_value).astype(np.float32)

    idx = tuple(int(v) for v in temporal_indices) if temporal_indices else (0, 1, 2)
    temporal_residual = np.zeros((len(idx), yaw_bins, occupancy.shape[0], occupancy.shape[1]), dtype=np.float32)

    for t_i, step in enumerate(idx):
        dyn_occ = _dynamic_occupancy_at_step(
            shape=occupancy.shape,
            dynamic_tracks=dynamic_tracks,
            dynamic_radii_m=dynamic_radii_m,
            resolution=resolution,
            step_idx=int(step),
        )
        occ_t = np.logical_or(occupancy, dyn_occ)
        t2d = compute_2d_dijkstra_field(occ_t, (goal_pose[0], goal_pose[1]), resolution)
        t2d = fill_unreachable(t2d, occ_t, fill_value=fill_value)
        t3d = _compute_teacher_3d_core(
            occupancy=occ_t,
            goal_pose=goal_pose,
            resolution=resolution,
            yaw_bins=yaw_bins,
            min_turn_radius=min_turn_radius,
            fill_value=fill_value,
            mode=mode,
            teacher_2d=t2d,
            esdf=esdf,
            hybrid_obstacle_alpha=hybrid_obstacle_alpha,
            hybrid_obstacle_threshold_m=hybrid_obstacle_threshold_m,
            rs_backend=rs_backend,
            rs_step_size=rs_step_size,
            planner_cfg=planner_cfg,
            vehicle_cfg=vehicle_cfg,
        )
        res_t = (t3d - rs_base).astype(np.float32)
        res_t[:, occ_t] = 0.0
        temporal_residual[t_i] = res_t

    return teacher_2d.astype(np.float32), teacher_3d, temporal_residual
