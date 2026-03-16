from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx3.common import activation_mask, path_tube, scene_bundle_nonholonomic, scene_bundle_standard, scene_gate


@dataclass(frozen=True)
class CX3BPSFParams:
    residual_alpha: float
    abstain_margin: float
    corridor_gain: float
    separator_gain: float
    hard_gain: float


def param_grid() -> list[CX3BPSFParams]:
    return [
        CX3BPSFParams(0.45, 0.00, 0.35, 1.10, 0.55),
        CX3BPSFParams(0.55, 0.00, 0.35, 1.10, 0.55),
        CX3BPSFParams(0.45, 0.08, 0.50, 1.35, 0.70),
        CX3BPSFParams(0.55, 0.08, 0.50, 1.35, 0.70),
    ]


def _delta2d(bundle: dict, occupancy: np.ndarray, params: CX3BPSFParams) -> tuple[np.ndarray, float]:
    gate = scene_gate(bundle['scene'], margin=float(params.abstain_margin), sharpness=10.0)
    if gate < 0.05:
        return np.zeros_like(bundle['focus'], dtype=np.float32), gate
    path_local = path_tube(bundle['path_dist'], radius_m=1.8)
    corridor_score = bundle['corridor'] * path_local * (1.0 - 0.4 * bundle['barrier'])
    separator_score = bundle['barrier'] * (1.0 - 0.35 * bundle['corridor'])
    hard_score = bundle['risk'] * bundle['morph_width'] * (1.0 - 0.25 * path_local)
    corridor_mask = activation_mask(corridor_score, occupancy, quantile=0.92, min_ratio=0.005, max_ratio=0.06)
    separator_mask = activation_mask(separator_score, occupancy, quantile=0.90, min_ratio=0.01, max_ratio=0.08)
    hard_mask = activation_mask(hard_score, occupancy, quantile=0.92, min_ratio=0.005, max_ratio=0.06)
    delta = gate * (
        - float(params.corridor_gain) * corridor_mask * corridor_score
        + float(params.separator_gain) * separator_mask * separator_score
        + float(params.hard_gain) * hard_mask * hard_score
    )
    return delta.astype(np.float32), gate


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX3BPSFParams) -> np.ndarray:
    bundle = scene_bundle_nonholonomic(case, predictor, cfg, float(params.residual_alpha))
    delta, gate = _delta2d(bundle, case['occupancy'], params)
    if gate < 0.05:
        return bundle['plain3d']
    field = bundle['plain3d'] + delta[None, ...]
    field = np.maximum(field, cfg.residual_floor_ratio * bundle['rs_base']).astype(np.float32)
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return field


def build_standard_field(sample, predictor, params: CX3BPSFParams) -> np.ndarray:
    bundle = scene_bundle_standard(sample, predictor)
    delta, gate = _delta2d(bundle, sample.occupancy, params)
    if gate < 0.05:
        return bundle['plain2d']
    field = bundle['plain2d'] + delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
