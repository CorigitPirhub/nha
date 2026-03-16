from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx3.common import activation_mask, path_tube, scene_bundle_nonholonomic, scene_bundle_standard, scene_gate


@dataclass(frozen=True)
class CX3ASAFEParams:
    residual_alpha: float
    abstain_margin: float
    support_quantile: float
    penalty_gain: float
    corridor_bonus: float


def param_grid() -> list[CX3ASAFEParams]:
    return [
        CX3ASAFEParams(0.45, 0.02, 0.90, 1.4, 0.35),
        CX3ASAFEParams(0.55, 0.02, 0.90, 1.4, 0.35),
        CX3ASAFEParams(0.45, 0.08, 0.93, 1.8, 0.45),
        CX3ASAFEParams(0.55, 0.08, 0.93, 1.8, 0.45),
    ]


def _delta2d(bundle: dict, occupancy: np.ndarray, params: CX3ASAFEParams) -> tuple[np.ndarray, float]:
    gate = scene_gate(bundle['scene'], margin=float(params.abstain_margin), sharpness=10.0)
    if gate < 0.05:
        return np.zeros_like(bundle['focus'], dtype=np.float32), gate
    path_local = path_tube(bundle['path_dist'], radius_m=1.6)
    penalty = (0.95 * bundle['barrier'] + 0.65 * bundle['morph_width'] + 0.45 * bundle['risk']) * (1.0 - 0.35 * bundle['corridor'])
    support = activation_mask(penalty, occupancy, quantile=float(params.support_quantile), min_ratio=0.01, max_ratio=0.10)
    reward_support = activation_mask(bundle['corridor'] * path_local, occupancy, quantile=0.94, min_ratio=0.005, max_ratio=0.05)
    delta = gate * (float(params.penalty_gain) * support * penalty - float(params.corridor_bonus) * reward_support * bundle['corridor'] * path_local)
    return delta.astype(np.float32), gate


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX3ASAFEParams) -> np.ndarray:
    bundle = scene_bundle_nonholonomic(case, predictor, cfg, float(params.residual_alpha))
    delta, gate = _delta2d(bundle, case['occupancy'], params)
    if gate < 0.05:
        return bundle['plain3d']
    field = bundle['plain3d'] + delta[None, ...]
    field = np.maximum(field, cfg.residual_floor_ratio * bundle['rs_base']).astype(np.float32)
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return field


def build_standard_field(sample, predictor, params: CX3ASAFEParams) -> np.ndarray:
    bundle = scene_bundle_standard(sample, predictor)
    delta, gate = _delta2d(bundle, sample.occupancy, params)
    if gate < 0.05:
        return bundle['plain2d']
    field = bundle['plain2d'] + delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
