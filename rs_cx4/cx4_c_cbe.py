from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard, hard_opportunity_map, scene_dual_scale, top_budget_mask


@dataclass(frozen=True)
class CX4CCBEParams:
    risk_lambda: float
    budget_base: float
    budget_gain: float
    gain: float


def param_grid() -> list[CX4CCBEParams]:
    return [
        CX4CCBEParams(0.85, 0.010, 0.020, 0.90),
        CX4CCBEParams(1.00, 0.010, 0.025, 1.00),
        CX4CCBEParams(1.10, 0.015, 0.030, 1.05),
        CX4CCBEParams(1.20, 0.020, 0.035, 1.10),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX4CCBEParams) -> tuple[np.ndarray, float]:
    budget_scale = scene_dual_scale(bundle['scene'], params.risk_lambda, 0.05, sharpness=10.0)
    budget_ratio = float(params.budget_base) + float(params.budget_gain) * budget_scale
    score = hard_opportunity_map(bundle)
    mask = top_budget_mask(score, occupancy, budget_ratio, min_ratio=0.002, max_ratio=0.05)
    delta = float(params.gain) * budget_scale * mask * score
    return delta.astype(np.float32), budget_scale


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX4CCBEParams) -> np.ndarray:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    delta, _ = _delta(bundle, case['occupancy'], params)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX4CCBEParams) -> np.ndarray:
    bundle, field = accepted_cx3d_standard(sample, predictor)
    delta, _ = _delta(bundle, sample.occupancy, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
