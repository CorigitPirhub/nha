from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard, improvement_margin_map, top_budget_mask


@dataclass(frozen=True)
class CX4DBBIParams:
    beta: float
    margin: float
    budget_ratio: float
    gain: float


def param_grid() -> list[CX4DBBIParams]:
    return [
        CX4DBBIParams(0.80, 0.02, 0.020, 0.70),
        CX4DBBIParams(0.90, 0.04, 0.025, 0.85),
        CX4DBBIParams(1.00, 0.06, 0.030, 1.00),
        CX4DBBIParams(1.10, 0.08, 0.035, 1.10),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX4DBBIParams) -> np.ndarray:
    margin_map = improvement_margin_map(bundle, params.beta)
    pos = np.maximum(margin_map - float(params.margin), 0.0).astype(np.float32)
    if float(np.max(pos)) <= 1e-8:
        return np.zeros_like(pos, dtype=np.float32)
    mask = top_budget_mask(pos, occupancy, params.budget_ratio, min_ratio=0.003, max_ratio=0.04)
    return float(params.gain) * mask * pos


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX4DBBIParams) -> np.ndarray:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, case['occupancy'], params)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX4DBBIParams) -> np.ndarray:
    bundle, field = accepted_cx3d_standard(sample, predictor)
    delta = _delta(bundle, sample.occupancy, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
