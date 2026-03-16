from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx2.common import (
    CXGlobalConfig,
    corridor_support_from_bridge,
    harmonic_dirichlet,
    nonholonomic_base_and_correction,
    normalize01,
    route_focus_map,
    select_gate_peaks,
    standard_base_and_correction,
)
from rs_cx.common import fuse_nonholonomic
from env.teacher import world_to_grid


@dataclass(frozen=True)
class CX2BHBFParams:
    residual_alpha: float
    off_bridge_gain: float
    bridge_pull_gain: float


def param_grid() -> list[CX2BHBFParams]:
    return [
        CX2BHBFParams(0.45, 2.0, 0.8),
        CX2BHBFParams(0.55, 2.0, 0.8),
        CX2BHBFParams(0.45, 3.0, 1.2),
        CX2BHBFParams(0.55, 3.0, 1.2),
    ]


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
    w = np.asarray(weights, dtype=np.float32)
    w = w / max(float(np.sum(w)), 1e-6)
    support = np.zeros_like(score_map, dtype=np.float32)
    for wi, bridge in zip(w, supports):
        support += float(wi) * bridge
    return normalize01(support)


def _case_geom(case: dict[str, Any], predictor, cfg: CXGlobalConfig, residual_alpha: float) -> dict[str, np.ndarray]:
    key = f'_cx2b_geom_a{float(residual_alpha):.3f}'
    cached = case.get(key, None)
    if isinstance(cached, dict):
        return cached
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(residual_alpha))
    res_mean = np.mean(corr3d, axis=0)
    focus = route_focus_map(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), residual_mean=res_mean)
    bridge_support = _build_bridge_support(case['occupancy'], focus, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    corridor_support = corridor_support_from_bridge(bridge_support, focus)
    cached = {
        'rs_base': rs_base.astype(np.float32),
        'corr3d': corr3d.astype(np.float32),
        'bridge_support': bridge_support.astype(np.float32),
        'corridor_support': corridor_support.astype(np.float32),
    }
    case[key] = cached
    return cached


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX2BHBFParams) -> np.ndarray:
    geom = _case_geom(case, predictor, cfg, params.residual_alpha)
    delta = float(params.off_bridge_gain) * normalize01(1.0 - geom['bridge_support']) * geom['corridor_support'] - float(params.bridge_pull_gain) * geom['bridge_support']
    corr_mod = geom['corr3d'] + delta[None, ...]
    return fuse_nonholonomic(geom['rs_base'], corr_mod, cfg.residual_floor_ratio)


def _sample_geom(sample, predictor) -> dict[str, np.ndarray]:
    cached = getattr(sample, '_cx2b_geom', None)
    if isinstance(cached, dict):
        return cached
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    focus = route_focus_map(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), residual_mean=corr2d)
    bridge_support = _build_bridge_support(sample.occupancy, focus, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution))
    corridor_support = corridor_support_from_bridge(bridge_support, focus)
    cached = {
        'base': base.astype(np.float32),
        'corr2d': corr2d.astype(np.float32),
        'bridge_support': bridge_support.astype(np.float32),
        'corridor_support': corridor_support.astype(np.float32),
    }
    setattr(sample, '_cx2b_geom', cached)
    return cached


def build_standard_field(sample, predictor, params: CX2BHBFParams) -> np.ndarray:
    geom = _sample_geom(sample, predictor)
    delta = float(params.off_bridge_gain) * normalize01(1.0 - geom['bridge_support']) * geom['corridor_support'] - float(params.bridge_pull_gain) * geom['bridge_support']
    field = geom['base'] + geom['corr2d'] + delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
