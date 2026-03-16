from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx7.common import accepted_bundle_nonholonomic, accepted_bundle_standard, duel_choice


@dataclass(frozen=True)
class CX7BCCDParams:
    misc_weight: float
    margin: float
    budget_ratio: float
    gain: float


def param_grid() -> list[CX7BCCDParams]:
    return [
        CX7BCCDParams(0.85, 0.02, 0.020, 0.80),
        CX7BCCDParams(1.00, 0.04, 0.025, 0.90),
        CX7BCCDParams(1.15, 0.06, 0.030, 1.00),
        CX7BCCDParams(1.30, 0.08, 0.035, 1.10),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX7BCCDParams) -> np.ndarray:
    _, best = duel_choice(bundle, occupancy, params.misc_weight, params.margin, params.budget_ratio)
    return float(params.gain) * best


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX7BCCDParams) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, case['occupancy'], params)
    return np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)


def build_standard_field(sample, predictor, params: CX7BCCDParams) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, sample.occupancy, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
