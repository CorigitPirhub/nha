from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx7.common import accepted_bundle_nonholonomic, accepted_bundle_standard, action_score_bank, arbitration_score, decoupled_specialist_memory, group_head_key, resize_like


@dataclass(frozen=True)
class CX7DDHAParams:
    arb_margin: float
    gain: float


def param_grid() -> list[CX7DDHAParams]:
    return [
        CX7DDHAParams(0.02, 0.80),
        CX7DDHAParams(0.04, 0.95),
        CX7DDHAParams(0.06, 1.10),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg, params: CX7DDHAParams) -> dict[str, Any]:
    return decoupled_specialist_memory(dev_cases, predictor, cfg)


def _specialist(bundle: dict, memory: dict[str, Any]) -> np.ndarray:
    key = group_head_key(bundle['scene'])
    proto = memory['proto'].get(key, None)
    if proto is None:
        acts = action_score_bank(bundle)
        proto = acts['separator'] if key == 'separator' else acts['narrow']
    return resize_like(np.asarray(proto, dtype=np.float32), bundle['focus'].shape)


def _delta(bundle: dict, memory: dict[str, Any], params: CX7DDHAParams) -> np.ndarray:
    arb = arbitration_score(bundle, params.arb_margin)
    if arb < 0.05:
        return np.zeros_like(bundle['focus'])
    head = _specialist(bundle, memory)
    return float(params.gain) * arb * np.maximum(head, 0.0)


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX7DDHAParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, memory, params)
    return np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)


def build_standard_field(sample, predictor, params: CX7DDHAParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, memory, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
