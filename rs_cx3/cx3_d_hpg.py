from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx3.common import activation_mask, path_tube, scene_bundle_nonholonomic, scene_gate
from rs_cx.common import line_distance_map, standard_base_and_correction
from rs_cx2.common import compute_sample_dijkstra_field, global_dilated_occupancy


@dataclass(frozen=True)
class CX3DHPGParams:
    residual_alpha: float
    abstain_margin: float
    guard_radius_m: float
    penalty_gain: float
    low_bridge_thr: float
    low_bridge_scale: float


def param_grid() -> list[CX3DHPGParams]:
    return [
        CX3DHPGParams(0.45, 0.04, 1.2, 1.0, 0.05, 0.50),
        CX3DHPGParams(0.55, 0.04, 1.2, 1.0, 0.05, 0.50),
        CX3DHPGParams(0.45, 0.10, 1.6, 1.3, 0.05, 0.35),
        CX3DHPGParams(0.55, 0.10, 1.6, 1.3, 0.05, 0.35),
        CX3DHPGParams(0.45, 0.10, 1.6, 1.3, 0.06, 0.25),
        CX3DHPGParams(0.55, 0.10, 1.6, 1.3, 0.06, 0.25),
    ]


def _delta2d(bundle: dict, occupancy: np.ndarray, params: CX3DHPGParams) -> tuple[np.ndarray, float]:
    gate = scene_gate(bundle['scene'], margin=float(params.abstain_margin), sharpness=12.0)
    if gate < 0.05:
        return np.zeros_like(bundle['focus'], dtype=np.float32), gate
    topo_guard = path_tube(bundle['path_dist'], radius_m=float(params.guard_radius_m))
    bottleneck = 0.6 * bundle['barrier'] + 0.4 * bundle['morph_width']
    guarded_score = topo_guard * bottleneck * (1.0 - 0.25 * bundle['corridor'])
    support = activation_mask(guarded_score, occupancy, quantile=0.92, min_ratio=0.005, max_ratio=0.06)
    if float(bundle['scene'].get('misc_likelihood', 0.0)) > float(bundle['scene'].get('hard_likelihood', 0.0)) + 0.05:
        return np.zeros_like(bundle['focus'], dtype=np.float32), 0.0
    bridge_diffuse = float(bundle['scene'].get('bridge_diffuse', 0.0))
    local_scale = 1.0
    if bridge_diffuse < float(params.low_bridge_thr):
        local_scale = float(params.low_bridge_scale)
    delta = gate * local_scale * float(params.penalty_gain) * support * guarded_score
    return delta.astype(np.float32), gate


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX3DHPGParams) -> np.ndarray:
    bundle = scene_bundle_nonholonomic(case, predictor, cfg, float(params.residual_alpha))
    delta, gate = _delta2d(bundle, case['occupancy'], params)
    if gate < 0.05:
        return bundle['plain3d']
    field = bundle['plain3d'] + delta[None, ...]
    field = np.maximum(field, cfg.residual_floor_ratio * bundle['rs_base']).astype(np.float32)
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return field


def _standard_guard_bundle(sample, predictor) -> dict:
    cached = getattr(sample, '_cx3d_standard_guard_bundle', None)
    if isinstance(cached, dict):
        return cached
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    plain2d = np.clip(base + corr2d, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    dil_occ = global_dilated_occupancy(sample.occupancy, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), iterations=1)
    orig = compute_sample_dijkstra_field(sample, sample.occupancy, 'cx3d_std_orig')
    dil = compute_sample_dijkstra_field(sample, dil_occ, 'cx3d_std_dil')
    barrier = np.clip((dil - orig) / np.maximum(orig, 1.0), 0.0, 1.0).astype(np.float32)
    path_dist = line_distance_map(sample.occupancy.shape, float(sample.resolution), (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1])).astype(np.float32)
    morph_width = np.clip(barrier * 0.5, 0.0, 1.0).astype(np.float32)
    corridor = np.clip(np.exp(-np.square(path_dist) / max(2.0 * 2.4 * 2.4, 1e-6)), 0.0, 1.0).astype(np.float32)
    focus = corridor.astype(np.float32)
    free = ~sample.occupancy
    openness = float(np.mean(np.maximum(esdf[free], 0.0) > 1.5)) if np.any(free) else 1.0
    near_line = corridor[free] > 0.6 if np.any(free) else np.asarray([], dtype=bool)
    path_open = float(np.mean(np.maximum(esdf[free][near_line], 0.0) > 1.2)) if np.any(near_line) else openness
    barrier_peak = float(np.quantile(barrier[free], 0.98)) if np.any(free) else 0.0
    focus_gap = float(np.quantile(focus[free], 0.98) - np.quantile(focus[free], 0.80)) if np.any(free) else 0.0
    hard_raw = 1.0 * barrier_peak + 0.6 * focus_gap - 0.8 * openness - 0.2 * path_open
    misc_raw = 1.0 * openness + 0.7 * path_open - 0.7 * barrier_peak - 0.4 * focus_gap
    scene = {'hard_likelihood': float(1.0 / (1.0 + np.exp(-4.0 * hard_raw))), 'misc_likelihood': float(1.0 / (1.0 + np.exp(-4.0 * misc_raw))), 'bridge_diffuse': 0.0, 'path_openness': path_open}
    cached = {'base': base.astype(np.float32), 'corr2d': corr2d.astype(np.float32), 'plain2d': plain2d, 'focus': focus, 'barrier': barrier, 'morph_width': morph_width, 'corridor': corridor, 'path_dist': path_dist, 'scene': scene}
    setattr(sample, '_cx3d_standard_guard_bundle', cached)
    return cached


def build_standard_field(sample, predictor, params: CX3DHPGParams) -> np.ndarray:
    bundle = _standard_guard_bundle(sample, predictor)
    delta, gate = _delta2d(bundle, sample.occupancy, params)
    if gate < 0.05:
        return bundle['plain2d']
    field = bundle['plain2d'] + delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
