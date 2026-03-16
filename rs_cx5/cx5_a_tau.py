from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx5.common import accepted_bundle_nonholonomic, accepted_bundle_standard, local_action_choice, scene_reward_scale


@dataclass(frozen=True)
class CX5ATAUParams:
    beta: float
    margin: float
    budget_ratio: float
    gain: float


def param_grid() -> list[CX5ATAUParams]:
    return [
        CX5ATAUParams(0.85, 0.02, 0.020, 0.80),
        CX5ATAUParams(0.95, 0.04, 0.025, 0.90),
        CX5ATAUParams(1.05, 0.06, 0.030, 1.00),
        CX5ATAUParams(1.15, 0.08, 0.035, 1.10),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX5ATAUParams) -> np.ndarray:
    _, best = local_action_choice(bundle, occupancy, beta=params.beta, margin=params.margin, budget_ratio=params.budget_ratio)
    reward = scene_reward_scale(bundle['scene'], margin=0.02, sharpness=10.0)
    return float(params.gain) * reward * best


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX5ATAUParams) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, case['occupancy'], params)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX5ATAUParams) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, sample.occupancy, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
