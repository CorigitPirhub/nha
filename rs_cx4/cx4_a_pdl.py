from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard, hard_opportunity_map, scene_dual_scale, top_budget_mask


@dataclass(frozen=True)
class CX4APDLParams:
    dual_lambda: float
    dual_margin: float
    budget_ratio: float
    gain: float


def param_grid() -> list[CX4APDLParams]:
    return [
        CX4APDLParams(0.75, 0.04, 0.020, 0.70),
        CX4APDLParams(0.90, 0.06, 0.025, 0.85),
        CX4APDLParams(1.05, 0.08, 0.030, 1.00),
        CX4APDLParams(1.20, 0.10, 0.035, 1.10),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX4APDLParams) -> tuple[np.ndarray, float]:
    dual = scene_dual_scale(bundle['scene'], params.dual_lambda, params.dual_margin, sharpness=12.0)
    if dual < 0.05:
        return np.zeros_like(bundle['focus'], dtype=np.float32), dual
    score = hard_opportunity_map(bundle)
    mask = top_budget_mask(score, occupancy, params.budget_ratio, min_ratio=0.003, max_ratio=0.04)
    delta = float(params.gain) * dual * mask * score
    return delta.astype(np.float32), dual


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX4APDLParams) -> np.ndarray:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    delta, dual = _delta(bundle, case['occupancy'], params)
    if dual < 0.05:
        return field
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX4APDLParams) -> np.ndarray:
    bundle, field = accepted_cx3d_standard(sample, predictor)
    delta, dual = _delta(bundle, sample.occupancy, params)
    if dual < 0.05:
        return field
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
