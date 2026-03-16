from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx6.common import accepted_bundle_nonholonomic, accepted_bundle_standard, action_score_bank, certificate_map, scene_bin_key, top_budget_mask


@dataclass(frozen=True)
class CX6CPMCParams:
    misc_weight: float
    uncert_weight: float
    margin: float
    budget_ratio: float
    gain: float


def param_grid() -> list[CX6CPMCParams]:
    return [
        CX6CPMCParams(0.80, 0.15, 0.02, 0.020, 0.80),
        CX6CPMCParams(0.95, 0.20, 0.04, 0.025, 0.90),
        CX6CPMCParams(1.10, 0.25, 0.06, 0.030, 1.00),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg, params: CX6CPMCParams) -> dict[str, Any]:
    bins = {}
    for item in dev_cases:
        bundle,_ = accepted_bundle_nonholonomic(item['case'], predictor, cfg)
        key = scene_bin_key(bundle['scene'])
        bank = action_score_bank(bundle)
        best = max([float(np.mean(v[~item['case']['occupancy']])) for v in bank.values()])
        bins.setdefault(key, []).append(best)
    calib = {k: float(np.mean(v)) for k,v in bins.items()}
    return {'calib': calib}


def _delta(bundle: dict, occupancy: np.ndarray, params: CX6CPMCParams, memory: dict[str, Any]) -> np.ndarray:
    bank = action_score_bank(bundle)
    key = scene_bin_key(bundle['scene'])
    calib = float(memory['calib'].get(key, 0.0))
    certs=[]
    for score in bank.values():
        cert = certificate_map(bundle, score, params.misc_weight, params.uncert_weight, params.margin)
        certs.append((cert + calib * 0.1).astype(np.float32))
    stack=np.stack(certs,axis=0)
    best=np.maximum(np.max(stack,axis=0),0.0).astype(np.float32)
    if float(np.max(best)) <= 1e-8:
        return np.zeros_like(best)
    mask=top_budget_mask(best, occupancy, params.budget_ratio, min_ratio=0.002, max_ratio=0.03)
    return float(params.gain) * best * mask


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX6CPMCParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, case['occupancy'], params, memory)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX6CPMCParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, sample.occupancy, params, memory)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
