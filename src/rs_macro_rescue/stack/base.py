from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

from rs_macro_rescue.config import DEFAULT_CONFIG
from rs_macro_rescue.env.esdf import compute_esdf
from rs_macro_rescue.env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from rs_macro_rescue.network.inference import NeuralHeuristicPredictor


@dataclass(frozen=True)
class CXGlobalConfig:
    residual_clip: float = 28.0
    residual_bias_quantile: float = 0.25
    residual_corridor_threshold: float = 0.9
    residual_corridor_suppress: float = 0.3
    residual_topq_quantile: float = 0.1
    residual_contrastive_bg_quantile: float = 0.62
    residual_contrastive_neg_scale: float = 0.16
    residual_contrastive_pos_scale: float = 1.25
    residual_floor_ratio: float = 0.62
    residual_open_boost_topq: float = 0.9
    residual_open_boost_min_line_clearance: float = 1.8
    rs_field_yaw_bins: int = 24


def normalize01(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    lo = float(np.nanmin(arr))
    hi = float(np.nanmax(arr))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo + 1e-9:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _world_to_grid(x: float, y: float, resolution: float, w: int, h: int) -> tuple[int, int]:
    gx = int(np.clip(np.floor(x / resolution), 0, w - 1))
    gy = int(np.clip(np.floor(y / resolution), 0, h - 1))
    return gx, gy


def _grid_to_world(ix: int, iy: int, resolution: float) -> tuple[float, float]:
    return (ix + 0.5) * resolution, (iy + 0.5) * resolution


def _neighbors8() -> list[tuple[int, int, float]]:
    rt2 = math.sqrt(2.0)
    return [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, rt2),
        (-1, 1, rt2),
        (1, -1, rt2),
        (1, 1, rt2),
    ]


def _astar_grid(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_expansions: int,
    heuristic_map: np.ndarray | None = None,
    heuristic_weight: float = 1.0,
    record_expanded: bool = False,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)

    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {
            "success": False,
            "expansions": 0,
            "runtime_ms": (time.perf_counter() - t0) * 1000.0,
            "path": [],
            "expanded": [],
        }

    def h_fn(ix: int, iy: int) -> float:
        if heuristic_map is None:
            return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)
        v = float(heuristic_map[iy, ix])
        if not np.isfinite(v):
            return 1e6
        return max(v, 0.0)

    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    counter = 0
    start = (sx, sy)
    goal = (gx, gy)
    g_cost: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    heapq.heappush(open_heap, (float(heuristic_weight) * h_fn(sx, sy), 0.0, counter, start))
    expanded: list[tuple[int, int]] = []
    expansions = 0
    nbrs = _neighbors8()

    while open_heap and expansions < max(int(max_expansions), 1):
        _, g, _, node = heapq.heappop(open_heap)
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue

        expansions += 1
        if record_expanded:
            expanded.append(node)

        if node == goal:
            path_grid: list[tuple[int, int]] = []
            cur: tuple[int, int] | None = node
            while cur is not None:
                path_grid.append(cur)
                cur = parent[cur]
            path_grid.reverse()
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": [_grid_to_world(ix, iy, resolution) for ix, iy in path_grid],
                "expanded": expanded,
            }

        x, y = node
        for dx, dy, step in nbrs:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h or occupancy[ny, nx]:
                continue
            ng = g + step * resolution
            nkey = (nx, ny)
            if ng + 1e-9 >= g_cost.get(nkey, float("inf")):
                continue
            g_cost[nkey] = ng
            parent[nkey] = node
            counter += 1
            nf = ng + float(heuristic_weight) * h_fn(nx, ny)
            heapq.heappush(open_heap, (nf, ng, counter, nkey))

    return {
        "success": False,
        "expansions": expansions,
        "runtime_ms": (time.perf_counter() - t0) * 1000.0,
        "path": [],
        "expanded": expanded,
    }


def _resolve_2d_heuristic(pred: np.ndarray, occupancy: np.ndarray) -> np.ndarray:
    if pred.ndim == 2:
        h2d = pred.astype(np.float32)
    else:
        h2d = np.min(pred.astype(np.float32), axis=0)
    h2d = np.where(np.isfinite(h2d), h2d, 1e6).astype(np.float32)
    h2d[occupancy] = 1e6
    return h2d


def _euclidean_field(
    occupancy: np.ndarray,
    goal_xy: tuple[float, float],
    resolution: float,
    fill_value: float = 1e6,
) -> np.ndarray:
    h, w = occupancy.shape
    yy, xx = np.mgrid[0:h, 0:w]
    wx = (xx + 0.5) * float(resolution)
    wy = (yy + 0.5) * float(resolution)
    field = np.hypot(wx - float(goal_xy[0]), wy - float(goal_xy[1])).astype(np.float32)
    field[occupancy] = float(fill_value)
    return field


def _compute_case_rs_field(case: dict[str, Any], yaw_bins_cap: int | None = None) -> np.ndarray:
    rs_cfg = RSConsistentCostConfig.from_configs(case["vehicle"], case["planner_cfg"])
    yaw_bins = int(max(8, getattr(case["planner_cfg"], "yaw_bins", DEFAULT_CONFIG.dataset.teacher_yaw_bins)))
    if yaw_bins_cap is not None and int(yaw_bins_cap) > 0:
        yaw_bins = int(min(yaw_bins, int(yaw_bins_cap)))
    rs_field = compute_reeds_shepp_field(
        occupancy=case["occupancy"],
        goal=case["goal"],
        resolution=case["resolution"],
        yaw_bins=yaw_bins,
        rho=float(case["vehicle"].min_turn_radius),
        fill_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
        step_size=float(DEFAULT_CONFIG.dataset.teacher_rs_step_size),
        backend=str(DEFAULT_CONFIG.dataset.teacher_rs_backend),
        cost_mode="planner_consistent",
        cost_cfg=rs_cfg,
    )
    return rs_field.astype(np.float32)


def _match_yaw_channels(field: np.ndarray, yaw_bins: int) -> np.ndarray:
    if field.ndim == 2:
        return np.repeat(field[None, ...], yaw_bins, axis=0).astype(np.float32)

    c, _, _ = field.shape
    if c == yaw_bins:
        return field.astype(np.float32)
    if c == 1:
        return np.repeat(field, yaw_bins, axis=0).astype(np.float32)

    dst = (np.arange(yaw_bins, dtype=np.float32) + 0.5) * (c / float(max(yaw_bins, 1))) - 0.5
    i0 = np.floor(dst).astype(np.int64) % c
    i1 = (i0 + 1) % c
    w = (dst - np.floor(dst)).astype(np.float32)
    return ((1.0 - w)[:, None, None] * field[i0] + w[:, None, None] * field[i1]).astype(np.float32)


def _shift2d_no_wrap(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.roll(np.roll(arr, shift=dy, axis=0), shift=dx, axis=1)
    if dy > 0:
        out[:dy, :] = 0.0
    elif dy < 0:
        out[dy:, :] = 0.0
    if dx > 0:
        out[:, :dx] = 0.0
    elif dx < 0:
        out[:, dx:] = 0.0
    return out


def _shift3d_no_wrap(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.roll(np.roll(arr, shift=dy, axis=1), shift=dx, axis=2)
    if dy > 0:
        out[:, :dy, :] = 0.0
    elif dy < 0:
        out[:, dy:, :] = 0.0
    if dx > 0:
        out[:, :, :dx] = 0.0
    elif dx < 0:
        out[:, :, dx:] = 0.0
    return out


def _transport_residual_obstacle_aware(
    residual_3d: np.ndarray,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    iters: int,
    step: float,
    clearance_sigma: float,
) -> np.ndarray:
    n_iters = int(max(iters, 0))
    step_size = float(np.clip(step, 0.0, 1.0))
    sigma = float(max(clearance_sigma, 1e-4))
    if n_iters <= 0 or step_size <= 0.0:
        return residual_3d.astype(np.float32, copy=True)

    free = (~occupancy.astype(bool)).astype(np.float32)
    if free.sum() <= 0.0:
        return residual_3d.astype(np.float32, copy=True)

    clearance = np.maximum(esdf.astype(np.float32), 0.0)
    z = residual_3d.astype(np.float32, copy=True)
    dirs = ((0, 1), (0, -1), (1, 0), (-1, 0))
    for _ in range(n_iters):
        accum = np.zeros_like(z, dtype=np.float32)
        wsum = np.zeros_like(clearance, dtype=np.float32)
        for dy, dx in dirs:
            neigh_free = _shift2d_no_wrap(free, dy=dy, dx=dx)
            neigh_clear = _shift2d_no_wrap(clearance, dy=dy, dx=dx)
            clear_sim = np.exp(-np.abs(clearance - neigh_clear) / sigma).astype(np.float32)
            w = (neigh_free * clear_sim).astype(np.float32)
            accum = accum + _shift3d_no_wrap(z, dy=dy, dx=dx) * w[None, ...]
            wsum = wsum + w
        avg = accum / np.maximum(wsum[None, ...], 1e-6)
        z = (z + step_size * (avg - z) * free[None, ...]).astype(np.float32)

    z[:, occupancy.astype(bool)] = 0.0
    return z


def _apply_residual_calibration(
    pred_res_3d: np.ndarray,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    residual_bias_quantile: float,
    corridor_threshold: float,
    corridor_suppress: float,
    topq_quantile: float,
    contrastive_bg_quantile: float = 0.0,
    contrastive_neg_scale: float = 0.0,
    contrastive_pos_scale: float = 1.0,
    transport_iters: int = 0,
    transport_step: float = 0.35,
    transport_clearance_sigma: float = 0.45,
    bottleneck_threshold: float = 0.0,
    bottleneck_blend: float = 0.0,
    bottleneck_gamma: float = 1.0,
    open_boost: float = 0.0,
    open_boost_topq: float = 0.0,
    bottleneck_dampen: float = 0.0,
) -> np.ndarray:
    out = pred_res_3d.astype(np.float32, copy=True)
    free = ~occupancy.astype(bool)

    q = float(np.clip(residual_bias_quantile, 0.0, 0.95))
    if q > 0.0 and np.any(free):
        flat = out[:, free].reshape(-1)
        if flat.size > 0:
            bias = float(np.quantile(flat, q))
            if np.isfinite(bias) and bias > 0.0:
                out = np.maximum(out - bias, 0.0).astype(np.float32)

    q_bg = float(np.clip(contrastive_bg_quantile, 0.0, 0.95))
    neg_scale = float(np.clip(contrastive_neg_scale, 0.0, 2.0))
    pos_scale = float(max(contrastive_pos_scale, 0.0))
    if q_bg > 0.0 and np.any(free):
        vals = out[:, free].reshape(-1)
        if vals.size > 0:
            bg = float(np.quantile(vals, q_bg))
            if np.isfinite(bg) and bg > 0.0:
                centered = out - bg
                out = (np.maximum(centered, 0.0) * pos_scale + np.minimum(centered, 0.0) * neg_scale).astype(np.float32)

    thr = float(max(corridor_threshold, 0.0))
    sup = float(np.clip(corridor_suppress, 0.0, 1.0))
    if thr > 0.0 and sup > 0.0:
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        corridor = np.clip((thr - clearance) / max(thr, 1e-6), 0.0, 1.0)
        out = (out * (1.0 - sup * corridor)[None, ...]).astype(np.float32)

    adapt_open = float(max(open_boost, 0.0))
    adapt_dampen = float(np.clip(bottleneck_dampen, 0.0, 1.0))
    adapt_thr = float(max(corridor_threshold, bottleneck_threshold, 0.0))
    if (adapt_open > 0.0 or adapt_dampen > 0.0) and adapt_thr > 0.0:
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        bottleneck = np.clip((adapt_thr - clearance) / max(adapt_thr, 1e-6), 0.0, 1.0)
        bott_w = np.power(bottleneck, float(max(bottleneck_gamma, 0.1))).astype(np.float32)
        open_w = (1.0 - bott_w).astype(np.float32)
        pos_raw = np.maximum(out, 0.0).astype(np.float32)
        q_boost = float(np.clip(open_boost_topq, 0.0, 0.999))
        if adapt_open > 0.0 and q_boost > 0.0 and np.any(free):
            vals = pos_raw[:, free].reshape(-1)
            vals = vals[vals > 0.0]
            if vals.size > 0:
                boost_mask = (pos_raw >= float(np.quantile(vals, q_boost))).astype(np.float32)
            else:
                boost_mask = np.zeros_like(pos_raw, dtype=np.float32)
        elif adapt_open > 0.0:
            boost_mask = (pos_raw > 0.0).astype(np.float32)
        else:
            boost_mask = np.zeros_like(pos_raw, dtype=np.float32)
        pos_gain = (1.0 + adapt_open * open_w[None, ...] * boost_mask).astype(np.float32)
        damp_gain = (1.0 - adapt_dampen * bott_w).astype(np.float32)
        out = (pos_raw * pos_gain * damp_gain[None, ...] + np.minimum(out, 0.0) * damp_gain[None, ...]).astype(np.float32)

    q_keep = float(np.clip(topq_quantile, 0.0, 0.999))
    if q_keep > 0.0 and np.any(free):
        vals = out[:, free].reshape(-1)
        vals_pos = vals[vals > 0.0]
        if vals_pos.size > 0:
            thr_keep = float(np.quantile(vals_pos, q_keep))
            if np.isfinite(thr_keep) and thr_keep > 0.0:
                keep_pos = (out > 0.0) & (out >= thr_keep)
                out = np.where(keep_pos | (out <= 0.0), out, 0.0).astype(np.float32)

    blend_thr = float(max(bottleneck_threshold, 0.0))
    blend_ratio = float(np.clip(bottleneck_blend, 0.0, 1.0))
    if int(max(transport_iters, 0)) > 0 and blend_ratio > 0.0 and blend_thr > 0.0:
        transported = _transport_residual_obstacle_aware(
            residual_3d=out,
            occupancy=occupancy,
            esdf=esdf,
            iters=int(transport_iters),
            step=float(transport_step),
            clearance_sigma=float(transport_clearance_sigma),
        )
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        bottleneck = np.clip((blend_thr - clearance) / max(blend_thr, 1e-6), 0.0, 1.0)
        local_w = (blend_ratio * np.power(bottleneck, float(max(bottleneck_gamma, 0.1)))).astype(np.float32)
        out = (out * (1.0 - local_w[None, ...]) + transported * local_w[None, ...]).astype(np.float32)

    out[:, occupancy.astype(bool)] = 0.0
    return out


def line_distance_map(shape: tuple[int, int], resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float]) -> np.ndarray:
    h, w = int(shape[0]), int(shape[1])
    xs = (np.arange(w, dtype=np.float32) + 0.5) * float(resolution)
    ys = (np.arange(h, dtype=np.float32) + 0.5) * float(resolution)
    xx, yy = np.meshgrid(xs, ys)
    ax, ay = float(start_xy[0]), float(start_xy[1])
    bx, by = float(goal_xy[0]), float(goal_xy[1])
    vx = bx - ax
    vy = by - ay
    denom = max(vx * vx + vy * vy, 1e-9)
    wx = xx - ax
    wy = yy - ay
    t = np.clip((wx * vx + wy * vy) / denom, 0.0, 1.0)
    qx = ax + t * vx
    qy = ay + t * vy
    return np.sqrt((xx - qx) ** 2 + (yy - qy) ** 2).astype(np.float32)


def local_std_map(field2d: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    arr = np.asarray(field2d, dtype=np.float32)
    mean = ndimage.gaussian_filter(arr, sigma=float(sigma))
    mean2 = ndimage.gaussian_filter(np.square(arr), sigma=float(sigma))
    var = np.maximum(mean2 - np.square(mean), 0.0)
    return np.sqrt(var).astype(np.float32)


def standard_base_and_correction(sample, predictor: NeuralHeuristicPredictor) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base = _euclidean_field(
        occupancy=sample.occupancy,
        goal_xy=(sample.goal[0], sample.goal[1]),
        resolution=float(sample.resolution),
        fill_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
    )
    pred = predictor.predict_field(
        occupancy=sample.occupancy,
        esdf=np.zeros_like(sample.occupancy, dtype=np.float32),
        start=sample.start,
        goal=sample.goal,
        resolution=float(sample.resolution),
        base_field_override=base,
    )
    pred2d = _resolve_2d_heuristic(pred, sample.occupancy)
    correction = np.maximum(pred2d - base, 0.0).astype(np.float32)
    esdf = compute_esdf(sample.occupancy, resolution=float(sample.resolution)).astype(np.float32)
    return base.astype(np.float32), correction.astype(np.float32), esdf


def nonholonomic_base_and_correction(case: dict[str, Any], predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, residual_alpha: float, *, open_boost: float = 0.0, corridor_suppress: float | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rs_cache_key = f'_rs_field_y{int(cfg.rs_field_yaw_bins)}'
    rs_base = case.get(rs_cache_key, None)
    if not isinstance(rs_base, np.ndarray):
        rs_base = _compute_case_rs_field(case, yaw_bins_cap=int(cfg.rs_field_yaw_bins)).astype(np.float32)
        case[rs_cache_key] = rs_base
    else:
        rs_base = np.asarray(rs_base, dtype=np.float32)
    yaw_bins = int(rs_base.shape[0]) if rs_base.ndim == 3 else 1

    pred_cache_key = '_pred_residual_raw'
    pred_res_raw = case.get(pred_cache_key, None)
    if not isinstance(pred_res_raw, np.ndarray):
        pred_res_raw = predictor.predict_residual_field(
            occupancy=case["occupancy"],
            esdf=case["esdf"],
            start=case["start"],
            goal=case["goal"],
            resolution=case["resolution"],
            dynamic_risk=case.get("dynamic_risk", None),
            dynamic_risk_seq=case.get("dynamic_risk_seq", None),
            vehicle_context=case.get("vehicle_context", None),
        )
        pred_res_raw = np.maximum(pred_res_raw, 0.0).astype(np.float32)
        case[pred_cache_key] = pred_res_raw
    else:
        pred_res_raw = np.asarray(pred_res_raw, dtype=np.float32)

    pred_res = np.clip(pred_res_raw * float(max(residual_alpha, 0.0)), 0.0, float(max(cfg.residual_clip, 0.0))).astype(np.float32)
    pred_res_3d = _match_yaw_channels(pred_res, yaw_bins=yaw_bins)
    base_res_3d = _apply_residual_calibration(
        pred_res_3d=pred_res_3d,
        occupancy=case["occupancy"],
        esdf=case["esdf"],
        residual_bias_quantile=cfg.residual_bias_quantile,
        corridor_threshold=cfg.residual_corridor_threshold,
        corridor_suppress=float(cfg.residual_corridor_suppress if corridor_suppress is None else corridor_suppress),
        topq_quantile=cfg.residual_topq_quantile,
        contrastive_bg_quantile=cfg.residual_contrastive_bg_quantile,
        contrastive_neg_scale=cfg.residual_contrastive_neg_scale,
        contrastive_pos_scale=cfg.residual_contrastive_pos_scale,
        transport_iters=0,
        transport_step=0.0,
        transport_clearance_sigma=1.0,
        bottleneck_threshold=0.0,
        bottleneck_blend=0.0,
        bottleneck_gamma=1.0,
        open_boost=float(max(open_boost, 0.0)),
        open_boost_topq=cfg.residual_open_boost_topq,
        bottleneck_dampen=0.0,
    )
    return rs_base, base_res_3d.astype(np.float32), case["esdf"].astype(np.float32)


def bottleneck_score(esdf: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float, corridor_thr: float = 1.0, line_sigma_m: float = 2.0) -> np.ndarray:
    clearance = np.maximum(np.asarray(esdf, dtype=np.float32), 0.0)
    narrow = np.clip((float(corridor_thr) - clearance) / max(float(corridor_thr), 1e-6), 0.0, 1.0)
    ld = line_distance_map(clearance.shape, resolution, start_xy, goal_xy)
    line_w = np.exp(-np.square(ld) / max(2.0 * float(line_sigma_m) * float(line_sigma_m), 1e-6)).astype(np.float32)
    return (narrow * line_w).astype(np.float32)


def uncertainty_score(base_res_3d: np.ndarray, esdf: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float) -> np.ndarray:
    res_mean = np.mean(np.asarray(base_res_3d, dtype=np.float32), axis=0)
    yaw_std = np.std(np.asarray(base_res_3d, dtype=np.float32), axis=0)
    spatial_std = local_std_map(res_mean, sigma=1.25)
    bott = bottleneck_score(esdf, start_xy, goal_xy, resolution, corridor_thr=1.0, line_sigma_m=2.0)
    score = normalize01(yaw_std) + normalize01(spatial_std) + 0.75 * normalize01(bott)
    return normalize01(score)


def fuse_nonholonomic(rs_base: np.ndarray, corr3d: np.ndarray, floor_ratio: float) -> np.ndarray:
    fused = (np.asarray(rs_base, dtype=np.float32) + np.asarray(corr3d, dtype=np.float32)).astype(np.float32)
    floor_ratio = float(np.clip(floor_ratio, 0.0, 1.0))
    if floor_ratio > 0.0:
        fused = np.maximum(fused, floor_ratio * np.asarray(rs_base, dtype=np.float32)).astype(np.float32)
    fused = np.clip(fused, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return fused


def run_standard_astar(sample, heuristic2d: np.ndarray, max_expansions: int) -> dict[str, Any]:
    return _astar_grid(
        occupancy=sample.occupancy,
        resolution=float(sample.resolution),
        start_xy=(sample.start[0], sample.start[1]),
        goal_xy=(sample.goal[0], sample.goal[1]),
        max_expansions=int(max_expansions),
        heuristic_map=np.asarray(heuristic2d, dtype=np.float32),
        heuristic_weight=1.0,
    )
