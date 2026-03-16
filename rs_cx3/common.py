from __future__ import annotations

import heapq
from typing import Any

import numpy as np
from scipy import ndimage

from config import DEFAULT_CONFIG
from env.teacher import compute_2d_dijkstra_field, fill_unreachable, world_to_grid
from rs_cx.common import CXGlobalConfig, fuse_nonholonomic, nonholonomic_base_and_correction, normalize01, standard_base_and_correction
from rs_cx2.common import (
    compute_case_dijkstra_field,
    compute_case_weighted_field,
    compute_sample_dijkstra_field,
    compute_sample_weighted_field,
    corridor_support_from_bridge,
    density_maps_from_geometry,
    global_dilated_occupancy,
    harmonic_dirichlet,
    line_distance_map,
    local_morph_occupancies,
    local_std_map,
    nearest_free_cell,
    route_focus_map,
    select_gate_peaks,
    weighted_dijkstra_field,
)


def _sample_cache(sample) -> dict[str, Any]:
    cache = getattr(sample, '_cx3_cache', None)
    if cache is None:
        cache = {}
        setattr(sample, '_cx3_cache', cache)
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


def quantile_free(x: np.ndarray, occupancy: np.ndarray, q: float) -> float:
    arr = np.asarray(x, dtype=np.float32)
    free = arr[~np.asarray(occupancy, dtype=bool)]
    if free.size == 0:
        return 0.0
    return float(np.quantile(free, float(np.clip(q, 0.0, 1.0))))


def _grid_shortest_path(occupancy: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float) -> list[tuple[int, int]]:
    occ = ensure_start_goal_free(occupancy, start_xy, goal_xy, resolution)
    h, w = occ.shape
    sx, sy = world_to_grid(start_xy[0], start_xy[1], resolution)
    gx, gy = world_to_grid(goal_xy[0], goal_xy[1], resolution)
    sx = int(np.clip(sx, 0, w - 1)); gx = int(np.clip(gx, 0, w - 1))
    sy = int(np.clip(sy, 0, h - 1)); gy = int(np.clip(gy, 0, h - 1))
    start = (sy, sx); goal = (gy, gx)
    if occ[start] or occ[goal]:
        return [start, goal]
    dist = np.full((h, w), np.inf, dtype=np.float32)
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    pq: list[tuple[float, int, int]] = [(0.0, start[0], start[1])]
    dist[start] = 0.0
    nbrs = [(-1,0,1.0),(1,0,1.0),(0,-1,1.0),(0,1,1.0),(-1,-1,np.sqrt(2.0)),(-1,1,np.sqrt(2.0)),(1,-1,np.sqrt(2.0)),(1,1,np.sqrt(2.0))]
    while pq:
        cur, y, x = heapq.heappop(pq)
        if cur > float(dist[y, x]):
            continue
        if (y, x) == goal:
            break
        for dx, dy, step in nbrs:
            nx = x + dx; ny = y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h or occ[ny, nx]:
                continue
            nd = cur + float(step) * float(resolution)
            if nd < float(dist[ny, nx]):
                dist[ny, nx] = nd
                parent[(ny, nx)] = (y, x)
                heapq.heappush(pq, (nd, ny, nx))
    if not np.isfinite(dist[goal]):
        return [start, goal]
    path = [goal]
    cur = goal
    while cur != start and cur in parent:
        cur = parent[cur]
        path.append(cur)
    path.reverse()
    return path


def _path_distance_map(shape: tuple[int, int], path_cells: list[tuple[int, int]], resolution: float) -> np.ndarray:
    mask = np.ones(shape, dtype=bool)
    for y, x in path_cells:
        yy = int(np.clip(y, 0, shape[0]-1)); xx = int(np.clip(x, 0, shape[1]-1))
        mask[yy, xx] = False
    dist = ndimage.distance_transform_edt(mask) * float(resolution)
    return dist.astype(np.float32)


def _build_bridge_support(occupancy: np.ndarray, score_map: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float, max_gates: int = 2) -> np.ndarray:
    gates = select_gate_peaks(score_map, occupancy, float(resolution), start_xy, goal_xy, max_points=max_gates, min_separation_m=2.2)
    gx, gy = world_to_grid(goal_xy[0], goal_xy[1], float(resolution))
    sx, sy = world_to_grid(start_xy[0], start_xy[1], float(resolution))
    supports = []
    weights = []
    for y, x in gates:
        u_goal = harmonic_dirichlet(occupancy, positive_rc=[(y, x)], negative_rc=[(gy, gx)], n_iter=70)
        u_start = harmonic_dirichlet(occupancy, positive_rc=[(y, x)], negative_rc=[(sy, sx)], n_iter=70)
        bridge = normalize01(u_goal * u_start)
        supports.append(bridge.astype(np.float32))
        weights.append(float(score_map[y, x]) + 1e-6)
    if not supports:
        return np.zeros_like(score_map, dtype=np.float32)
    weight = np.asarray(weights, dtype=np.float32)
    weight = weight / max(float(np.sum(weight)), 1e-6)
    out = np.zeros_like(score_map, dtype=np.float32)
    for wi, bridge in zip(weight, supports):
        out += float(wi) * bridge
    return normalize01(out)


def activation_mask(score: np.ndarray, occupancy: np.ndarray, quantile: float, min_ratio: float = 0.02, max_ratio: float = 0.25) -> np.ndarray:
    arr = np.asarray(score, dtype=np.float32)
    occ = np.asarray(occupancy, dtype=bool)
    free = ~occ
    if not np.any(free):
        return np.zeros_like(arr, dtype=np.float32)
    thr = float(np.quantile(arr[free], float(np.clip(quantile, 0.5, 0.995))))
    mask = (arr >= thr) & free
    ratio = float(np.mean(mask[free])) if np.any(free) else 0.0
    if ratio < float(min_ratio):
        # ensure at least a few active cells
        thr = float(np.quantile(arr[free], max(0.0, 1.0 - float(min_ratio))))
        mask = (arr >= thr) & free
    if ratio > float(max_ratio):
        thr = float(np.quantile(arr[free], min(0.999, 1.0 - float(max_ratio))))
        mask = (arr >= thr) & free
    return mask.astype(np.float32)


def protected_misc_metrics(occupancy: np.ndarray, esdf: np.ndarray, focus: np.ndarray, barrier: np.ndarray, bridge: np.ndarray, path_dist: np.ndarray) -> dict[str, float]:
    occ = np.asarray(occupancy, dtype=bool)
    free = ~occ
    focus_arr = np.asarray(focus, dtype=np.float32)
    barrier_arr = np.asarray(barrier, dtype=np.float32)
    bridge_arr = np.asarray(bridge, dtype=np.float32)
    esdf_arr = np.maximum(np.asarray(esdf, dtype=np.float32), 0.0)
    path_arr = np.asarray(path_dist, dtype=np.float32)
    if not np.any(free):
        return {'hard_likelihood': 0.0, 'misc_likelihood': 1.0, 'focus_gap': 0.0, 'focus_mass': 0.0, 'barrier_peak': 0.0, 'openness': 1.0, 'path_openness': 1.0, 'bridge_diffuse': 1.0}
    focus_q98 = float(np.quantile(focus_arr[free], 0.98))
    focus_q80 = float(np.quantile(focus_arr[free], 0.80))
    focus_gap = max(focus_q98 - focus_q80, 0.0)
    focus_mass = float(np.mean(focus_arr[free] >= float(np.quantile(focus_arr[free], 0.75))))
    barrier_peak = float(np.quantile(barrier_arr[free], 0.98))
    openness = float(np.mean(esdf_arr[free] > 1.5))
    near_path = path_arr[free] <= 1.5
    path_openness = float(np.mean(esdf_arr[free][near_path] > 1.2)) if np.any(near_path) else openness
    bridge_mass = float(np.mean(bridge_arr[free] > float(np.quantile(bridge_arr[free], 0.80))))
    bridge_peak = float(np.quantile(bridge_arr[free], 0.98))
    bridge_diffuse = float(np.clip(bridge_mass - 0.15 * bridge_peak, 0.0, 1.0))
    hard_raw = 1.3 * focus_gap + 1.1 * barrier_peak + 0.35 * bridge_peak - 0.5 * openness - 0.25 * path_openness
    misc_raw = 0.95 * openness + 0.7 * focus_mass + 0.55 * path_openness + 0.35 * bridge_diffuse - 0.8 * barrier_peak - 0.7 * focus_gap
    hard_likelihood = float(1.0 / (1.0 + np.exp(-4.0 * hard_raw)))
    misc_likelihood = float(1.0 / (1.0 + np.exp(-4.0 * misc_raw)))
    return {
        'hard_likelihood': hard_likelihood,
        'misc_likelihood': misc_likelihood,
        'focus_gap': float(focus_gap),
        'focus_mass': float(focus_mass),
        'barrier_peak': float(barrier_peak),
        'openness': float(openness),
        'path_openness': float(path_openness),
        'bridge_diffuse': float(bridge_diffuse),
    }


def scene_bundle_nonholonomic(case: dict[str, Any], predictor, cfg: CXGlobalConfig, residual_alpha: float) -> dict[str, Any]:
    key = f'_cx3_bundle_a{float(residual_alpha):.3f}'
    cached = case.get(key, None)
    if isinstance(cached, dict):
        return cached
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(residual_alpha))
    plain3d = fuse_nonholonomic(rs_base, corr3d, cfg.residual_floor_ratio)
    res_mean = np.mean(corr3d, axis=0)
    focus = route_focus_map(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), residual_mean=res_mean)
    opt_occ, con_occ, _ = local_morph_occupancies(case['occupancy'], focus, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), focus_quantile=0.72, focus_dilate_iters=2)
    orig_dij = compute_case_dijkstra_field(case, case['occupancy'], f'cx3_orig_a{float(residual_alpha):.3f}')
    opt_dij = compute_case_dijkstra_field(case, opt_occ, f'cx3_opt_a{float(residual_alpha):.3f}')
    con_dij = compute_case_dijkstra_field(case, con_occ, f'cx3_con_a{float(residual_alpha):.3f}')
    morph_width = normalize01(np.maximum(con_dij - opt_dij, 0.0))
    dil_occ = global_dilated_occupancy(case['occupancy'], (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), iterations=1)
    dil_dij = compute_case_dijkstra_field(case, dil_occ, f'cx3_dil_a{float(residual_alpha):.3f}')
    barrier = normalize01(np.maximum(dil_dij - orig_dij, 0.0))
    bridge = _build_bridge_support(case['occupancy'], focus, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    corridor = corridor_support_from_bridge(bridge, focus)
    capacity, risk = density_maps_from_geometry(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), residual_mean=res_mean)
    path = _grid_shortest_path(case['occupancy'], (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    path_dist = _path_distance_map(case['occupancy'].shape, path, float(case['resolution']))
    scene = protected_misc_metrics(case['occupancy'], esdf, focus, barrier, bridge, path_dist)
    bundle = {
        'rs_base': rs_base.astype(np.float32),
        'corr3d': corr3d.astype(np.float32),
        'plain3d': plain3d.astype(np.float32),
        'esdf': esdf.astype(np.float32),
        'focus': focus.astype(np.float32),
        'morph_width': morph_width.astype(np.float32),
        'barrier': barrier.astype(np.float32),
        'bridge': bridge.astype(np.float32),
        'corridor': corridor.astype(np.float32),
        'capacity': capacity.astype(np.float32),
        'risk': risk.astype(np.float32),
        'path_dist': path_dist.astype(np.float32),
        'scene': scene,
    }
    case[key] = bundle
    return bundle


def scene_bundle_standard(sample, predictor) -> dict[str, Any]:
    cache = _sample_cache(sample)
    key = 'bundle'
    cached = cache.get(key, None)
    if isinstance(cached, dict):
        return cached
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    plain2d = np.clip(base + corr2d, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    focus = route_focus_map(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), residual_mean=corr2d)
    opt_occ, con_occ, _ = local_morph_occupancies(sample.occupancy, focus, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), focus_quantile=0.72, focus_dilate_iters=2)
    orig = compute_sample_dijkstra_field(sample, sample.occupancy, 'cx3_orig')
    opt = compute_sample_dijkstra_field(sample, opt_occ, 'cx3_opt')
    con = compute_sample_dijkstra_field(sample, con_occ, 'cx3_con')
    morph_width = normalize01(np.maximum(con - opt, 0.0))
    dil_occ = global_dilated_occupancy(sample.occupancy, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), iterations=1)
    dil = compute_sample_dijkstra_field(sample, dil_occ, 'cx3_dil')
    barrier = normalize01(np.maximum(dil - orig, 0.0))
    bridge = _build_bridge_support(sample.occupancy, focus, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution))
    corridor = corridor_support_from_bridge(bridge, focus)
    capacity, risk = density_maps_from_geometry(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), residual_mean=corr2d)
    path = _grid_shortest_path(sample.occupancy, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution))
    path_dist = _path_distance_map(sample.occupancy.shape, path, float(sample.resolution))
    scene = protected_misc_metrics(sample.occupancy, esdf, focus, barrier, bridge, path_dist)
    bundle = {
        'base': base.astype(np.float32),
        'corr2d': corr2d.astype(np.float32),
        'plain2d': plain2d.astype(np.float32),
        'esdf': esdf.astype(np.float32),
        'focus': focus.astype(np.float32),
        'morph_width': morph_width.astype(np.float32),
        'barrier': barrier.astype(np.float32),
        'bridge': bridge.astype(np.float32),
        'corridor': corridor.astype(np.float32),
        'capacity': capacity.astype(np.float32),
        'risk': risk.astype(np.float32),
        'path_dist': path_dist.astype(np.float32),
        'scene': scene,
    }
    cache[key] = bundle
    return bundle


def scene_gate(scene: dict[str, float], margin: float, sharpness: float = 8.0) -> float:
    hard = float(scene.get('hard_likelihood', 0.0))
    misc = float(scene.get('misc_likelihood', 0.0))
    z = float(sharpness) * (hard - misc - float(margin))
    gate = float(1.0 / (1.0 + np.exp(-z)))
    if misc > hard + float(margin):
        gate *= 0.25
    return gate


def path_tube(path_dist: np.ndarray, radius_m: float) -> np.ndarray:
    d = np.asarray(path_dist, dtype=np.float32)
    return np.exp(-np.square(d) / max(2.0 * float(radius_m) * float(radius_m), 1e-6)).astype(np.float32)


__all__ = [
    'CXGlobalConfig',
    'activation_mask',
    'compute_case_dijkstra_field',
    'compute_case_weighted_field',
    'compute_sample_dijkstra_field',
    'compute_sample_weighted_field',
    'corridor_support_from_bridge',
    'density_maps_from_geometry',
    'fuse_nonholonomic',
    'normalize01',
    'path_tube',
    'protected_misc_metrics',
    'quantile_free',
    'scene_bundle_nonholonomic',
    'scene_bundle_standard',
    'scene_gate',
    'weighted_dijkstra_field',
]
