from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx2.common import (
    CXGlobalConfig,
    compute_case_dijkstra_field,
    compute_sample_dijkstra_field,
    global_dilated_occupancy,
    nonholonomic_base_and_correction,
    normalize01,
    route_focus_map,
    standard_base_and_correction,
)
from rs_cx.common import fuse_nonholonomic, line_distance_map


@dataclass(frozen=True)
class CX2CBCEParams:
    residual_alpha: float
    barrier_gain: float
    exemption_gain: float


def param_grid() -> list[CX2CBCEParams]:
    return [
        CX2CBCEParams(0.45, 1.8, 0.35),
        CX2CBCEParams(0.55, 1.8, 0.35),
        CX2CBCEParams(0.45, 2.8, 0.50),
        CX2CBCEParams(0.55, 2.8, 0.50),
    ]


def _case_geom(case: dict[str, Any], predictor, cfg: CXGlobalConfig, residual_alpha: float) -> dict[str, np.ndarray]:
    key = f'_cx2c_geom_a{float(residual_alpha):.3f}'
    cached = case.get(key, None)
    if isinstance(cached, dict):
        return cached
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(residual_alpha))
    res_mean = np.mean(corr3d, axis=0)
    focus = route_focus_map(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), residual_mean=res_mean)
    dil_occ = global_dilated_occupancy(case['occupancy'], (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), iterations=1)
    orig = compute_case_dijkstra_field(case, case['occupancy'], 'cx2c_orig')
    dil = compute_case_dijkstra_field(case, dil_occ, 'cx2c_dil')
    line = np.exp(-np.square(line_distance_map(esdf.shape, float(case['resolution']), (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]))) / max(2.0 * 2.4 * 2.4, 1e-6)).astype(np.float32)
    cached = {'rs_base': rs_base.astype(np.float32), 'corr3d': corr3d.astype(np.float32), 'barrier': normalize01(np.maximum(dil - orig, 0.0)), 'positive': normalize01(0.75 * focus + 0.55 * line)}
    case[key] = cached
    return cached


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX2CBCEParams) -> np.ndarray:
    geom = _case_geom(case, predictor, cfg, params.residual_alpha)
    barrier_eff = geom['barrier'] * np.clip(1.0 - float(params.exemption_gain) * geom['positive'], 0.15, 1.0)
    corr_mod = geom['corr3d'] + float(params.barrier_gain) * barrier_eff[None, ...]
    return fuse_nonholonomic(geom['rs_base'], corr_mod, cfg.residual_floor_ratio)


def _sample_geom(sample, predictor) -> dict[str, np.ndarray]:
    cached = getattr(sample, '_cx2c_geom', None)
    if isinstance(cached, dict):
        return cached
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    focus = route_focus_map(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), residual_mean=corr2d)
    dil_occ = global_dilated_occupancy(sample.occupancy, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), iterations=1)
    orig = compute_sample_dijkstra_field(sample, sample.occupancy, 'cx2c_orig')
    dil = compute_sample_dijkstra_field(sample, dil_occ, 'cx2c_dil')
    line = np.exp(-np.square(line_distance_map(esdf.shape, float(sample.resolution), (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]))) / max(2.0 * 2.4 * 2.4, 1e-6)).astype(np.float32)
    cached = {'base': base.astype(np.float32), 'corr2d': corr2d.astype(np.float32), 'barrier': normalize01(np.maximum(dil - orig, 0.0)), 'positive': normalize01(0.75 * focus + 0.55 * line)}
    setattr(sample, '_cx2c_geom', cached)
    return cached


def build_standard_field(sample, predictor, params: CX2CBCEParams) -> np.ndarray:
    geom = _sample_geom(sample, predictor)
    barrier_eff = geom['barrier'] * np.clip(1.0 - float(params.exemption_gain) * geom['positive'], 0.15, 1.0)
    field = geom['base'] + geom['corr2d'] + float(params.barrier_gain) * barrier_eff
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
