from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx2.common import (
    CXGlobalConfig,
    compute_case_weighted_field,
    compute_sample_dijkstra_field,
    compute_sample_weighted_field,
    density_maps_from_geometry,
    nonholonomic_base_and_correction,
    standard_base_and_correction,
)
from rs_cx.common import fuse_nonholonomic


@dataclass(frozen=True)
class CX2DPIFParams:
    residual_alpha: float
    capacity_gain: float
    risk_gain: float
    delta_gain: float


def param_grid() -> list[CX2DPIFParams]:
    return [
        CX2DPIFParams(0.45, 0.25, 0.45, 0.85),
        CX2DPIFParams(0.55, 0.25, 0.45, 0.85),
        CX2DPIFParams(0.45, 0.40, 0.60, 1.10),
        CX2DPIFParams(0.55, 0.40, 0.60, 1.10),
    ]


def _step_weight(capacity: np.ndarray, risk: np.ndarray, params: CX2DPIFParams) -> np.ndarray:
    weight = 1.0 + float(params.risk_gain) * np.asarray(risk, dtype=np.float32) - float(params.capacity_gain) * np.asarray(capacity, dtype=np.float32)
    return np.clip(weight, 0.25, 3.0).astype(np.float32)


def _case_geom(case: dict[str, Any], predictor, cfg: CXGlobalConfig, residual_alpha: float) -> dict[str, np.ndarray]:
    key = f'_cx2d_geom_a{float(residual_alpha):.3f}'
    cached = case.get(key, None)
    if isinstance(cached, dict):
        return cached
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(residual_alpha))
    res_mean = np.mean(corr3d, axis=0)
    capacity, risk = density_maps_from_geometry(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), residual_mean=res_mean)
    cached = {
        'rs_base': rs_base.astype(np.float32),
        'corr3d': corr3d.astype(np.float32),
        'capacity': capacity.astype(np.float32),
        'risk': risk.astype(np.float32),
    }
    case[key] = cached
    return cached


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX2DPIFParams) -> np.ndarray:
    geom = _case_geom(case, predictor, cfg, params.residual_alpha)
    step_weight = _step_weight(geom['capacity'], geom['risk'], params)
    weighted = compute_case_weighted_field(case, step_weight, f'cx2d_{params.capacity_gain:.2f}_{params.risk_gain:.2f}')
    base_orig = case.get('_cx2d_orig_dijkstra', None)
    if not isinstance(base_orig, np.ndarray):
        from rs_cx2.common import weighted_dijkstra_field, ensure_start_goal_free
        occ = ensure_start_goal_free(case['occupancy'], (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
        base_orig = weighted_dijkstra_field(occ, (case['goal'][0], case['goal'][1]), float(case['resolution']), np.ones_like(step_weight, dtype=np.float32))
        case['_cx2d_orig_dijkstra'] = base_orig.astype(np.float32)
    delta = np.clip(weighted - np.asarray(base_orig, dtype=np.float32), -4.0, 8.0).astype(np.float32)
    corr_mod = geom['corr3d'] + float(params.delta_gain) * delta[None, ...]
    return fuse_nonholonomic(geom['rs_base'], corr_mod, cfg.residual_floor_ratio)


def _sample_geom(sample, predictor) -> dict[str, np.ndarray]:
    cached = getattr(sample, '_cx2d_geom', None)
    if isinstance(cached, dict):
        return cached
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    capacity, risk = density_maps_from_geometry(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), residual_mean=corr2d)
    orig = compute_sample_dijkstra_field(sample, sample.occupancy, 'cx2d_orig')
    cached = {
        'base': base.astype(np.float32),
        'corr2d': corr2d.astype(np.float32),
        'capacity': capacity.astype(np.float32),
        'risk': risk.astype(np.float32),
        'orig': orig.astype(np.float32),
    }
    setattr(sample, '_cx2d_geom', cached)
    return cached


def build_standard_field(sample, predictor, params: CX2DPIFParams) -> np.ndarray:
    geom = _sample_geom(sample, predictor)
    step_weight = _step_weight(geom['capacity'], geom['risk'], params)
    weighted = compute_sample_weighted_field(sample, step_weight, f'cx2d_{params.capacity_gain:.2f}_{params.risk_gain:.2f}')
    delta = np.clip(weighted - geom['orig'], -4.0, 8.0).astype(np.float32)
    field = geom['base'] + geom['corr2d'] + float(params.delta_gain) * delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
