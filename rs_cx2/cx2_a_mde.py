from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx2.common import (
    CXGlobalConfig,
    compute_case_dijkstra_field,
    compute_sample_dijkstra_field,
    fuse_nonholonomic,
    local_morph_occupancies,
    nonholonomic_base_and_correction,
    normalize01,
    route_focus_map,
    standard_base_and_correction,
)


@dataclass(frozen=True)
class CX2AMDEParams:
    residual_alpha: float
    open_gain: float
    close_gain: float
    residual_trust: float


def param_grid() -> list[CX2AMDEParams]:
    return [
        CX2AMDEParams(0.45, 0.35, 0.55, 0.15),
        CX2AMDEParams(0.55, 0.35, 0.55, 0.15),
        CX2AMDEParams(0.45, 0.50, 0.70, 0.25),
        CX2AMDEParams(0.55, 0.50, 0.70, 0.25),
    ]


def _case_geom(case: dict[str, Any], predictor, cfg: CXGlobalConfig, residual_alpha: float) -> dict[str, np.ndarray]:
    key = f'_cx2a_geom_a{float(residual_alpha):.3f}'
    cached = case.get(key, None)
    if isinstance(cached, dict):
        return cached
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(residual_alpha))
    res_mean = np.mean(corr3d, axis=0)
    focus = route_focus_map(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), residual_mean=res_mean)
    opt_occ, con_occ, _ = local_morph_occupancies(case['occupancy'], focus, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), focus_quantile=0.72, focus_dilate_iters=2)
    orig_dij = compute_case_dijkstra_field(case, case['occupancy'], 'cx2a_orig')
    opt_dij = compute_case_dijkstra_field(case, opt_occ, 'cx2a_opt')
    con_dij = compute_case_dijkstra_field(case, con_occ, 'cx2a_con')
    cached = {
        'rs_base': rs_base.astype(np.float32),
        'corr3d': corr3d.astype(np.float32),
        'focus': focus.astype(np.float32),
        'orig_dij': orig_dij.astype(np.float32),
        'opt_dij': opt_dij.astype(np.float32),
        'con_dij': con_dij.astype(np.float32),
    }
    case[key] = cached
    return cached


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX2AMDEParams) -> np.ndarray:
    geom = _case_geom(case, predictor, cfg, params.residual_alpha)
    width = normalize01(np.maximum(geom['con_dij'] - geom['opt_dij'], 0.0))
    stable = 1.0 - width
    delta2d = float(params.open_gain) * stable * (geom['opt_dij'] - geom['orig_dij']) + float(params.close_gain) * width * (geom['con_dij'] - geom['orig_dij'])
    corr_scale = np.clip(1.0 - float(params.residual_trust) * width, 0.55, 1.0).astype(np.float32)
    corr_mod = geom['corr3d'] * corr_scale[None, ...] + delta2d[None, ...]
    return fuse_nonholonomic(geom['rs_base'], corr_mod, cfg.residual_floor_ratio)


def _sample_geom(sample, predictor) -> dict[str, np.ndarray]:
    cached = getattr(sample, '_cx2a_geom', None)
    if isinstance(cached, dict):
        return cached
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    focus = route_focus_map(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), residual_mean=corr2d)
    opt_occ, con_occ, _ = local_morph_occupancies(sample.occupancy, focus, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), focus_quantile=0.72, focus_dilate_iters=2)
    orig_occ = compute_sample_dijkstra_field(sample, sample.occupancy, 'cx2a_orig')
    opt_field = compute_sample_dijkstra_field(sample, opt_occ, 'cx2a_opt')
    con_field = compute_sample_dijkstra_field(sample, con_occ, 'cx2a_con')
    cached = {'base': base.astype(np.float32), 'corr2d': corr2d.astype(np.float32), 'orig_occ': orig_occ.astype(np.float32), 'opt_field': opt_field.astype(np.float32), 'con_field': con_field.astype(np.float32)}
    setattr(sample, '_cx2a_geom', cached)
    return cached


def build_standard_field(sample, predictor, params: CX2AMDEParams) -> np.ndarray:
    geom = _sample_geom(sample, predictor)
    width = normalize01(np.maximum(geom['con_field'] - geom['opt_field'], 0.0))
    stable = 1.0 - width
    delta = float(params.open_gain) * stable * (geom['opt_field'] - geom['orig_occ']) + float(params.close_gain) * width * (geom['con_field'] - geom['orig_occ'])
    corr_scale = np.clip(1.0 - float(params.residual_trust) * width, 0.55, 1.0).astype(np.float32)
    field = geom['base'] + geom['corr2d'] * corr_scale + delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
