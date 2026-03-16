from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx3.common import activation_mask, path_tube, scene_bundle_nonholonomic, scene_bundle_standard, scene_gate


@dataclass(frozen=True)
class CX3CCCPParams:
    residual_alpha: float
    abstain_margin: float
    positive_gain: float
    negative_gain: float
    misc_veto_gain: float


def param_grid() -> list[CX3CCCPParams]:
    return [
        CX3CCCPParams(0.45, 0.00, 1.10, 0.25, 0.45),
        CX3CCCPParams(0.55, 0.00, 1.10, 0.25, 0.45),
        CX3CCCPParams(0.45, 0.08, 1.45, 0.35, 0.65),
        CX3CCCPParams(0.55, 0.08, 1.45, 0.35, 0.65),
    ]


def _scene_misc_veto(scene: dict[str, float]) -> float:
    bridge_diffuse = float(scene.get('bridge_diffuse', 0.0))
    path_open = float(scene.get('path_openness', 0.0))
    openness = float(scene.get('openness', 0.0))
    misc = float(scene.get('misc_likelihood', 0.0))
    hard = float(scene.get('hard_likelihood', 0.0))
    z1 = 1.0 / (1.0 + np.exp(-18.0 * (bridge_diffuse - 0.06)))
    z2 = 1.0 / (1.0 + np.exp(-18.0 * (path_open - 0.93)))
    z3 = 1.0 / (1.0 + np.exp(-18.0 * (openness - 0.64)))
    z4 = 1.0 / (1.0 + np.exp(-12.0 * ((misc - hard) + 0.02)))
    return float(z1 * z2 * z3 * z4)


def _delta2d(bundle: dict, occupancy: np.ndarray, params: CX3CCCPParams) -> tuple[np.ndarray, float]:
    gate = scene_gate(bundle['scene'], margin=float(params.abstain_margin), sharpness=10.0)
    if gate < 0.05:
        return np.zeros_like(bundle['focus'], dtype=np.float32), gate
    path_local = path_tube(bundle['path_dist'], radius_m=1.7)
    pos_bar = activation_mask(bundle['barrier'], occupancy, quantile=0.90, min_ratio=0.01, max_ratio=0.08)
    pos_morph = activation_mask(bundle['morph_width'], occupancy, quantile=0.90, min_ratio=0.01, max_ratio=0.08)
    pos_risk = activation_mask(bundle['risk'], occupancy, quantile=0.92, min_ratio=0.005, max_ratio=0.06)
    pos_count = pos_bar + pos_morph + pos_risk
    pos_score = (0.5 * bundle['barrier'] + 0.3 * bundle['morph_width'] + 0.2 * bundle['risk']) * (pos_count >= 2.0) * (1.0 - 0.35 * bundle['corridor'])
    neg_support = activation_mask(bundle['corridor'] * path_local, occupancy, quantile=0.94, min_ratio=0.005, max_ratio=0.05)
    neg_guard = (bundle['barrier'] < float(np.quantile(bundle['barrier'][~occupancy], 0.60) if np.any(~occupancy) else 0.5)).astype(np.float32)
    neg_morph = (bundle['morph_width'] < float(np.quantile(bundle['morph_width'][~occupancy], 0.60) if np.any(~occupancy) else 0.5)).astype(np.float32)
    neg_score = neg_support * neg_guard * neg_morph * bundle['corridor'] * path_local

    misc_veto = _scene_misc_veto(bundle['scene'])
    protect_scale = max(0.0, 1.0 - float(params.misc_veto_gain) * misc_veto)
    delta = gate * (float(params.positive_gain) * protect_scale * pos_score - float(params.negative_gain) * neg_score)
    return delta.astype(np.float32), gate


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX3CCCPParams) -> np.ndarray:
    bundle = scene_bundle_nonholonomic(case, predictor, cfg, float(params.residual_alpha))
    delta, gate = _delta2d(bundle, case['occupancy'], params)
    if gate < 0.05:
        return bundle['plain3d']
    field = bundle['plain3d'] + delta[None, ...]
    field = np.maximum(field, cfg.residual_floor_ratio * bundle['rs_base']).astype(np.float32)
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return field


def build_standard_field(sample, predictor, params: CX3CCCPParams) -> np.ndarray:
    bundle = scene_bundle_standard(sample, predictor)
    delta, gate = _delta2d(bundle, sample.occupancy, params)
    if gate < 0.05:
        return bundle['plain2d']
    field = bundle['plain2d'] + delta
    field = np.clip(field, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    field[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return field
