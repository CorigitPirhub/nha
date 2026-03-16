from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx7.common import accepted_bundle_nonholonomic, accepted_bundle_standard, evidence_accumulation_map, top_budget_mask


@dataclass(frozen=True)
class CX7AEACParams:
    misc_weight: float
    uncert_weight: float
    support_weight: float
    margin: float
    budget_ratio: float
    gain: float


def param_grid() -> list[CX7AEACParams]:
    return [
        CX7AEACParams(0.85, 0.20, 0.20, 0.02, 0.020, 0.80),
        CX7AEACParams(1.00, 0.25, 0.25, 0.04, 0.025, 0.90),
        CX7AEACParams(1.15, 0.30, 0.30, 0.06, 0.030, 1.00),
        CX7AEACParams(1.30, 0.35, 0.35, 0.08, 0.035, 1.10),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX7AEACParams) -> np.ndarray:
    cert = evidence_accumulation_map(bundle, occupancy, params.misc_weight, params.uncert_weight, params.support_weight, params.margin)
    pos = np.maximum(cert, 0.0).astype(np.float32)
    if float(np.max(pos)) <= 1e-8:
        return np.zeros_like(pos)
    mask = top_budget_mask(pos, occupancy, params.budget_ratio, min_ratio=0.002, max_ratio=0.03)
    return float(params.gain) * pos * mask


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX7AEACParams) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, case['occupancy'], params)
    return np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)


def build_standard_field(sample, predictor, params: CX7AEACParams) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, sample.occupancy, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
