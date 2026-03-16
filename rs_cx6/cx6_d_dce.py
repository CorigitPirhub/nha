from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx6.common import accepted_bundle_nonholonomic, accepted_bundle_standard, flange_opportunity_map, group_head_key, misc_penalty_map, narrow_opportunity_map, resize_like, separator_opportunity_map


@dataclass(frozen=True)
class CX6DDCEParams:
    gain: float
    misc_weight: float


def param_grid() -> list[CX6DDCEParams]:
    return [
        CX6DDCEParams(0.80, 0.80),
        CX6DDCEParams(0.95, 0.95),
        CX6DDCEParams(1.10, 1.10),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg, params: CX6DDCEParams) -> dict[str, Any]:
    groups={'protected':[],'narrow':[],'flange':[],'separator':[]}
    for item in dev_cases:
        bundle,_ = accepted_bundle_nonholonomic(item['case'], predictor, cfg)
        key = group_head_key(bundle['scene'])
        if key == 'narrow':
            head = narrow_opportunity_map(bundle)
        elif key == 'flange':
            head = flange_opportunity_map(bundle)
        elif key == 'separator':
            head = separator_opportunity_map(bundle)
        else:
            head = np.zeros_like(bundle['focus'], dtype=np.float32)
        groups[key].append(head.astype(np.float32))
    proto={}
    for k,v in groups.items():
        proto[k]=np.mean(np.stack(v,axis=0),axis=0).astype(np.float32) if v else None
    return {'proto': proto}


def _delta(bundle: dict, params: CX6DDCEParams, memory: dict[str, Any]) -> np.ndarray:
    key = group_head_key(bundle['scene'])
    proto = memory['proto'].get(key, None)
    if proto is None:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    head = resize_like(proto, bundle['focus'].shape)
    margin = np.maximum(head - float(params.misc_weight) * misc_penalty_map(bundle), 0.0)
    return float(params.gain) * margin


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX6DDCEParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, params, memory)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX6DDCEParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, params, memory)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
