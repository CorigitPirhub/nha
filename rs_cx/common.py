from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

from config import DEFAULT_CONFIG
from env.esdf import compute_esdf
from network.inference import NeuralHeuristicPredictor
from scripts.evaluate_baselines import (
    _apply_residual_calibration,
    _astar_grid,
    _compute_case_rs_field,
    _euclidean_field,
    _match_yaw_channels,
    _resolve_2d_heuristic,
)


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
