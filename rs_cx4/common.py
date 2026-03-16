from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig, normalize01
from rs_cx3.common import activation_mask, path_tube, scene_bundle_nonholonomic, scene_bundle_standard
from rs_cx3.cx3_d_hpg import CX3DHPGParams, build_nonholonomic_field as build_cx3d_nonholonomic, build_standard_field as build_cx3d_standard


ACCEPTED_CX3D_PARAMS = CX3DHPGParams(
    residual_alpha=0.55,
    abstain_margin=0.1,
    guard_radius_m=1.6,
    penalty_gain=1.3,
    low_bridge_thr=0.06,
    low_bridge_scale=0.25,
)


def accepted_cx3d_nonholonomic(case: dict[str, Any], predictor, cfg: CXGlobalConfig) -> tuple[dict[str, Any], np.ndarray]:
    cache_key = '_cx4_accepted_cx3d_field'
    field = case.get(cache_key, None)
    bundle = scene_bundle_nonholonomic(case, predictor, cfg, float(ACCEPTED_CX3D_PARAMS.residual_alpha))
    if not isinstance(field, np.ndarray):
        field = build_cx3d_nonholonomic(case, predictor, cfg, ACCEPTED_CX3D_PARAMS).astype(np.float32)
        case[cache_key] = field
    else:
        field = np.asarray(field, dtype=np.float32)
    return bundle, field


def accepted_cx3d_standard(sample, predictor) -> tuple[dict[str, Any], np.ndarray]:
    field = getattr(sample, '_cx4_accepted_cx3d_field', None)
    bundle = scene_bundle_standard(sample, predictor)
    if not isinstance(field, np.ndarray):
        field = build_cx3d_standard(sample, predictor, ACCEPTED_CX3D_PARAMS).astype(np.float32)
        setattr(sample, '_cx4_accepted_cx3d_field', field)
    else:
        field = np.asarray(field, dtype=np.float32)
    return bundle, field


def hard_opportunity_map(bundle: dict[str, Any]) -> np.ndarray:
    score = (0.45 * bundle['barrier'] + 0.25 * bundle['morph_width'] + 0.30 * bundle['risk']) * (1.0 - 0.15 * bundle['corridor'])
    score = score * path_tube(bundle['path_dist'], radius_m=1.7)
    return normalize01(score)


def misc_penalty_map(bundle: dict[str, Any]) -> np.ndarray:
    openness = normalize01(np.maximum(bundle['esdf'], 0.0)) if 'esdf' in bundle else np.ones_like(bundle['focus'], dtype=np.float32)
    score = (0.55 * bundle['corridor'] + 0.30 * bundle['focus'] + 0.15 * openness) * (1.0 - 0.35 * bundle['barrier'])
    return normalize01(score)


def scene_dual_scale(scene: dict[str, float], dual_lambda: float, margin: float, sharpness: float = 12.0) -> float:
    hard = float(scene.get('hard_likelihood', 0.0))
    misc = float(scene.get('misc_likelihood', 0.0))
    z = float(sharpness) * (hard - float(dual_lambda) * misc - float(margin))
    return float(1.0 / (1.0 + np.exp(-z)))


def improvement_margin_map(bundle: dict[str, Any], beta: float) -> np.ndarray:
    hard = hard_opportunity_map(bundle)
    misc = misc_penalty_map(bundle)
    return (hard - float(beta) * misc).astype(np.float32)


def top_budget_mask(score: np.ndarray, occupancy: np.ndarray, budget_ratio: float, min_ratio: float = 0.005, max_ratio: float = 0.06) -> np.ndarray:
    ratio = float(np.clip(budget_ratio, min_ratio, max_ratio))
    quantile = float(np.clip(1.0 - ratio, 0.0, 0.995))
    return activation_mask(score, occupancy, quantile=quantile, min_ratio=min_ratio, max_ratio=max_ratio)


def sparse_patch_from_hotspots(bundle: dict[str, Any], occupancy: np.ndarray, top_quantile: float = 0.985) -> np.ndarray:
    hard = hard_opportunity_map(bundle)
    mask = activation_mask(hard, occupancy, quantile=top_quantile, min_ratio=0.002, max_ratio=0.03)
    return mask.astype(np.float32)


def patch_similarity(bundle: dict[str, Any], proto: dict[str, float]) -> float:
    scene = bundle['scene']
    diff = abs(float(scene.get('hard_likelihood', 0.0)) - float(proto['hard_likelihood']))
    diff += abs(float(scene.get('misc_likelihood', 0.0)) - float(proto['misc_likelihood']))
    diff += 0.5 * abs(float(scene.get('bridge_diffuse', 0.0)) - float(proto['bridge_diffuse']))
    return float(np.exp(-4.0 * diff))


__all__ = [
    'ACCEPTED_CX3D_PARAMS',
    'accepted_cx3d_nonholonomic',
    'accepted_cx3d_standard',
    'hard_opportunity_map',
    'improvement_margin_map',
    'misc_penalty_map',
    'patch_similarity',
    'scene_dual_scale',
    'sparse_patch_from_hotspots',
    'top_budget_mask',
]
