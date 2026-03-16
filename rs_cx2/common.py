from __future__ import annotations

import heapq
from typing import Any

import numpy as np
from scipy import ndimage

from config import DEFAULT_CONFIG
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from env.teacher import compute_2d_dijkstra_field, fill_unreachable, world_to_grid
from rs_cx.common import (
    CXGlobalConfig,
    bottleneck_score,
    fuse_nonholonomic,
    line_distance_map,
    local_std_map,
    nonholonomic_base_and_correction,
    normalize01,
    run_standard_astar,
    standard_base_and_correction,
    uncertainty_score,
)


def _sample_cache(sample) -> dict[str, Any]:
    cache = getattr(sample, '_cx2_cache', None)
    if cache is None:
        cache = {}
        setattr(sample, '_cx2_cache', cache)
    return cache


def ensure_start_goal_free(occupancy: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=bool).copy()
    h, w = occ.shape
    for x, y in [start_xy, goal_xy]:
        gx, gy = world_to_grid(float(x), float(y), float(resolution))
        gx = int(np.clip(gx, 0, w - 1))
        gy = int(np.clip(gy, 0, h - 1))
        occ[gy, gx] = False
    return occ


def collapse_yaw_min(field3d: np.ndarray) -> np.ndarray:
    arr = np.asarray(field3d, dtype=np.float32)
    if arr.ndim == 2:
        return arr.astype(np.float32)
    return np.min(arr, axis=0).astype(np.float32)


def compute_case_rs_field_custom(case: dict[str, Any], occupancy: np.ndarray, cfg: CXGlobalConfig, cache_key: str) -> np.ndarray:
    key = f'_cx2_{cache_key}_rs_field_y{int(cfg.rs_field_yaw_bins)}'
    cached = case.get(key, None)
    if isinstance(cached, np.ndarray):
        return np.asarray(cached, dtype=np.float32)
    occ = ensure_start_goal_free(occupancy, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    rs_cfg = RSConsistentCostConfig.from_configs(case['vehicle'], case['planner_cfg'])
    yaw_bins = int(max(8, min(int(getattr(case['planner_cfg'], 'yaw_bins', cfg.rs_field_yaw_bins)), int(cfg.rs_field_yaw_bins))))
    field = compute_reeds_shepp_field(
        occupancy=occ,
        goal=case['goal'],
        resolution=float(case['resolution']),
        yaw_bins=yaw_bins,
        rho=float(case['vehicle'].min_turn_radius),
        fill_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
        step_size=float(DEFAULT_CONFIG.dataset.teacher_rs_step_size),
        backend=str(DEFAULT_CONFIG.dataset.teacher_rs_backend),
        cost_mode='planner_consistent',
        cost_cfg=rs_cfg,
    ).astype(np.float32)
    case[key] = field
    return field


def compute_sample_dijkstra_field(sample, occupancy: np.ndarray, cache_key: str) -> np.ndarray:
    cache = _sample_cache(sample)
    key = f'{cache_key}_field'
    cached = cache.get(key, None)
    if isinstance(cached, np.ndarray):
        return np.asarray(cached, dtype=np.float32)
    occ = ensure_start_goal_free(occupancy, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution))
    field = compute_2d_dijkstra_field(occ, (sample.goal[0], sample.goal[1]), float(sample.resolution))
    field = fill_unreachable(field, occ, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    cache[key] = field
    return field


def weighted_dijkstra_field(occupancy: np.ndarray, goal_xy: tuple[float, float], resolution: float, step_weight: np.ndarray) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=bool)
    weight = np.asarray(step_weight, dtype=np.float32)
    h, w = occ.shape
    gx, gy = world_to_grid(float(goal_xy[0]), float(goal_xy[1]), float(resolution))
    gx = int(np.clip(gx, 0, w - 1))
    gy = int(np.clip(gy, 0, h - 1))
    dist = np.full((h, w), np.inf, dtype=np.float32)
    if occ[gy, gx]:
        return fill_unreachable(dist, occ, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)

    pq: list[tuple[float, int, int]] = [(0.0, gy, gx)]
    dist[gy, gx] = 0.0
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
    while pq:
        cur_d, y, x = heapq.heappop(pq)
        if cur_d > float(dist[y, x]):
            continue
        for dx, dy, step in neighbors:
            nx = x + dx
            ny = y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h or occ[ny, nx]:
                continue
            edge = 0.5 * float(weight[y, x] + weight[ny, nx]) * float(step) * float(resolution)
            nd = cur_d + max(edge, 1e-6)
            if nd < float(dist[ny, nx]):
                dist[ny, nx] = nd
                heapq.heappush(pq, (nd, ny, nx))
    return fill_unreachable(dist, occ, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)


def compute_sample_weighted_field(sample, step_weight: np.ndarray, cache_key: str) -> np.ndarray:
    cache = _sample_cache(sample)
    key = f'{cache_key}_field'
    cached = cache.get(key, None)
    if isinstance(cached, np.ndarray):
        return np.asarray(cached, dtype=np.float32)
    occ = ensure_start_goal_free(sample.occupancy, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution))
    field = weighted_dijkstra_field(occ, (sample.goal[0], sample.goal[1]), float(sample.resolution), step_weight=step_weight)
    cache[key] = field
    return field


def compute_case_weighted_field(case: dict[str, Any], step_weight: np.ndarray, cache_key: str) -> np.ndarray:
    key = f'_cx2_{cache_key}_weighted_field'
    cached = case.get(key, None)
    if isinstance(cached, np.ndarray):
        return np.asarray(cached, dtype=np.float32)
    occ = ensure_start_goal_free(case['occupancy'], (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    field = weighted_dijkstra_field(occ, (case['goal'][0], case['goal'][1]), float(case['resolution']), step_weight=step_weight)
    case[key] = field
    return field

def compute_case_dijkstra_field(case: dict[str, Any], occupancy: np.ndarray, cache_key: str) -> np.ndarray:
    key = f'_cx2_{cache_key}_dijkstra_field'
    cached = case.get(key, None)
    if isinstance(cached, np.ndarray):
        return np.asarray(cached, dtype=np.float32)
    occ = ensure_start_goal_free(occupancy, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    field = compute_2d_dijkstra_field(occ, (case['goal'][0], case['goal'][1]), float(case['resolution']))
    field = fill_unreachable(field, occ, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    case[key] = field
    return field


def route_focus_map(esdf: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float, residual_mean: np.ndarray | None = None) -> np.ndarray:
    bott = bottleneck_score(esdf, start_xy, goal_xy, resolution, corridor_thr=1.2, line_sigma_m=2.4)
    line = np.exp(-np.square(line_distance_map(esdf.shape, resolution, start_xy, goal_xy)) / max(2.0 * 2.6 * 2.6, 1e-6)).astype(np.float32)
    score = 0.9 * normalize01(bott) + 0.7 * normalize01(line)
    if residual_mean is not None:
        score = score + 0.45 * normalize01(local_std_map(np.asarray(residual_mean, dtype=np.float32), sigma=1.2))
    return normalize01(score)


def nearest_free_cell(occupancy: np.ndarray, target_rc: tuple[int, int]) -> tuple[int, int]:
    occ = np.asarray(occupancy, dtype=bool)
    h, w = occ.shape
    ty = int(np.clip(target_rc[0], 0, h - 1))
    tx = int(np.clip(target_rc[1], 0, w - 1))
    if not occ[ty, tx]:
        return ty, tx
    ys, xs = np.nonzero(~occ)
    if ys.size == 0:
        return ty, tx
    dist2 = np.square(ys - ty) + np.square(xs - tx)
    idx = int(np.argmin(dist2))
    return int(ys[idx]), int(xs[idx])


def select_gate_peaks(score_map: np.ndarray, occupancy: np.ndarray, resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float], max_points: int = 2, min_separation_m: float = 2.0) -> list[tuple[int, int]]:
    score = ndimage.gaussian_filter(np.asarray(score_map, dtype=np.float32), sigma=1.0)
    occ = np.asarray(occupancy, dtype=bool)
    h, w = occ.shape
    start_rc = nearest_free_cell(occ, world_to_grid(start_xy[0], start_xy[1], resolution)[::-1])
    goal_rc = nearest_free_cell(occ, world_to_grid(goal_xy[0], goal_xy[1], resolution)[::-1])
    ys, xs = np.nonzero(~occ)
    if ys.size == 0:
        return [start_rc]
    order = np.argsort(score[ys, xs])[::-1]
    picked: list[tuple[int, int]] = []
    min_sep = float(min_separation_m / max(float(resolution), 1e-6))
    for idx in order:
        y = int(ys[idx])
        x = int(xs[idx])
        if (y - start_rc[0]) ** 2 + (x - start_rc[1]) ** 2 < max(min_sep * min_sep, 4.0):
            continue
        if (y - goal_rc[0]) ** 2 + (x - goal_rc[1]) ** 2 < max(min_sep * min_sep, 4.0):
            continue
        if any((y - py) ** 2 + (x - px) ** 2 < min_sep * min_sep for py, px in picked):
            continue
        if float(score[y, x]) <= 0.0:
            continue
        picked.append((y, x))
        if len(picked) >= int(max_points):
            break
    if picked:
        return picked
    mid_xy = ((float(start_xy[0]) + float(goal_xy[0])) * 0.5, (float(start_xy[1]) + float(goal_xy[1])) * 0.5)
    gx, gy = world_to_grid(mid_xy[0], mid_xy[1], resolution)
    return [nearest_free_cell(occ, (gy, gx))]


def harmonic_dirichlet(occupancy: np.ndarray, positive_rc: list[tuple[int, int]], negative_rc: list[tuple[int, int]], n_iter: int = 80) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=bool)
    free = ~occ
    u = np.full(occ.shape, 0.5, dtype=np.float32)
    pos_mask = np.zeros_like(occ, dtype=bool)
    neg_mask = np.zeros_like(occ, dtype=bool)
    for y, x in positive_rc:
        yy, xx = nearest_free_cell(occ, (y, x))
        pos_mask[yy, xx] = True
    for y, x in negative_rc:
        yy, xx = nearest_free_cell(occ, (y, x))
        neg_mask[yy, xx] = True
    fixed = pos_mask | neg_mask | occ
    u[pos_mask] = 1.0
    u[neg_mask] = 0.0
    kernel = np.asarray([[0.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    free_f = free.astype(np.float32)
    denom = ndimage.convolve(free_f, kernel, mode='constant', cval=0.0)
    denom = np.maximum(denom, 1.0)
    for _ in range(int(max(n_iter, 1))):
        numer = ndimage.convolve(u * free_f, kernel, mode='constant', cval=0.0)
        updated = numer / denom
        u[free & ~fixed] = updated[free & ~fixed]
        u[pos_mask] = 1.0
        u[neg_mask] = 0.0
        u[occ] = 0.0
    return normalize01(u)


def local_morph_occupancies(occupancy: np.ndarray, focus_map: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float, focus_quantile: float = 0.75, focus_dilate_iters: int = 2) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    occ = ensure_start_goal_free(occupancy, start_xy, goal_xy, resolution)
    free_mask = ~occ
    focus = np.asarray(focus_map, dtype=np.float32)
    if np.any(free_mask):
        thr = float(np.quantile(focus[free_mask], float(np.clip(focus_quantile, 0.5, 0.95))))
    else:
        thr = 0.5
    raw = (focus >= max(thr, 0.45)) & free_mask
    if not np.any(raw):
        raw = free_mask & (focus >= float(np.max(focus) - 1e-6))
    mask = ndimage.binary_dilation(raw, iterations=int(max(focus_dilate_iters, 1)))
    eroded = ndimage.binary_erosion(occ, iterations=1, border_value=1)
    dilated = ndimage.binary_dilation(occ, iterations=1)
    optimistic = occ.copy()
    conservative = occ.copy()
    optimistic[mask] = eroded[mask]
    conservative[mask] = dilated[mask]
    optimistic = ensure_start_goal_free(optimistic, start_xy, goal_xy, resolution)
    conservative = ensure_start_goal_free(conservative, start_xy, goal_xy, resolution)
    return optimistic, conservative, mask.astype(np.float32)


def global_dilated_occupancy(occupancy: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float, iterations: int = 1) -> np.ndarray:
    occ = ensure_start_goal_free(occupancy, start_xy, goal_xy, resolution)
    dilated = ndimage.binary_dilation(occ, iterations=int(max(iterations, 1)))
    return ensure_start_goal_free(dilated, start_xy, goal_xy, resolution)


def corridor_support_from_bridge(bridge_support: np.ndarray, focus_map: np.ndarray) -> np.ndarray:
    return normalize01(0.7 * normalize01(bridge_support) + 0.5 * normalize01(focus_map))


def density_maps_from_geometry(esdf: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float, residual_mean: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    clearance = np.maximum(np.asarray(esdf, dtype=np.float32), 0.0)
    line = np.exp(-np.square(line_distance_map(clearance.shape, resolution, start_xy, goal_xy)) / max(2.0 * 2.5 * 2.5, 1e-6)).astype(np.float32)
    narrow = bottleneck_score(clearance, start_xy, goal_xy, resolution, corridor_thr=1.2, line_sigma_m=2.6)
    cap = normalize01(np.minimum(clearance, 2.0)) * normalize01(0.8 * line + 0.5 * narrow + 0.2)
    risk = normalize01(0.8 * normalize01(local_std_map(cap, sigma=1.2)) + 0.9 * normalize01(narrow) + 0.5 * (1.0 - normalize01(line)))
    if residual_mean is not None:
        risk = normalize01(risk + 0.4 * normalize01(local_std_map(np.asarray(residual_mean, dtype=np.float32), sigma=1.0)))
    return cap.astype(np.float32), risk.astype(np.float32)


__all__ = [
    'CXGlobalConfig',
    'bottleneck_score',
    'collapse_yaw_min',
    'compute_case_rs_field_custom',
    'compute_case_dijkstra_field',
    'compute_case_weighted_field',
    'compute_sample_dijkstra_field',
    'compute_sample_weighted_field',
    'corridor_support_from_bridge',
    'density_maps_from_geometry',
    'fuse_nonholonomic',
    'global_dilated_occupancy',
    'harmonic_dirichlet',
    'line_distance_map',
    'local_morph_occupancies',
    'local_std_map',
    'nearest_free_cell',
    'nonholonomic_base_and_correction',
    'normalize01',
    'route_focus_map',
    'run_standard_astar',
    'select_gate_peaks',
    'standard_base_and_correction',
    'uncertainty_score',
    'weighted_dijkstra_field',
]
