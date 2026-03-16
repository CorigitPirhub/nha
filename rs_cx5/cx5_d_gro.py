from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage

from config import DEFAULT_CONFIG
from rs_cx5.common import accepted_bundle_nonholonomic, accepted_bundle_standard, flange_opportunity_map, hard_opportunity_map, misc_penalty_map, narrow_opportunity_map, separator_opportunity_map


@dataclass(frozen=True)
class CX5DGROParams:
    misc_weight: float
    hard_gain: float
    margin: float


def param_grid() -> list[CX5DGROParams]:
    return [
        CX5DGROParams(0.85, 0.80, 0.02),
        CX5DGROParams(1.00, 0.90, 0.04),
        CX5DGROParams(1.15, 1.00, 0.06),
        CX5DGROParams(1.30, 1.10, 0.08),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg, params: CX5DGROParams) -> dict[str, Any]:
    heads=[]
    for item in dev_cases:
        bundle,_ = accepted_bundle_nonholonomic(item['case'], predictor, cfg)
        scen = str(item['case']['scenario'])
        if scen == 'narrow_passage':
            head = narrow_opportunity_map(bundle)
        elif scen == 'flange':
            head = flange_opportunity_map(bundle)
        else:
            head = separator_opportunity_map(bundle)
        heads.append({'scenario': scen, 'head': head.astype(np.float32), 'scene': dict(bundle['scene'])})
    return {'heads': heads}


def _resize_head(arr: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.shape == target_shape:
        return arr
    zoom = (float(target_shape[0]) / max(arr.shape[0], 1), float(target_shape[1]) / max(arr.shape[1], 1))
    resized = ndimage.zoom(arr, zoom=zoom, order=1).astype(np.float32)
    out = np.zeros(target_shape, dtype=np.float32)
    h = min(target_shape[0], resized.shape[0])
    w = min(target_shape[1], resized.shape[1])
    out[:h, :w] = resized[:h, :w]
    return out


def _group_head(bundle: dict, memory: dict[str, Any]) -> np.ndarray:
    if not memory['heads']:
        return hard_opportunity_map(bundle)
    hard = float(bundle['scene'].get('hard_likelihood', 0.0))
    misc = float(bundle['scene'].get('misc_likelihood', 0.0))
    if misc > hard:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    bridge = float(bundle['scene'].get('bridge_diffuse', 0.0))
    if bridge < 0.03:
        candidates=[h['head'] for h in memory['heads'] if h['scenario']=='narrow_passage']
    elif bridge < 0.08:
        candidates=[h['head'] for h in memory['heads'] if h['scenario']=='flange']
    else:
        candidates=[h['head'] for h in memory['heads']]
    if not candidates:
        candidates=[hard_opportunity_map(bundle)]
    resized = [_resize_head(c, bundle['focus'].shape) for c in candidates]
    return np.mean(np.stack(resized,axis=0),axis=0).astype(np.float32)


def _delta(bundle: dict, memory: dict[str, Any], params: CX5DGROParams) -> np.ndarray:
    head = _group_head(bundle, memory)
    margin = np.maximum(head - float(params.misc_weight) * misc_penalty_map(bundle) - float(params.margin), 0.0)
    return float(params.hard_gain) * margin


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX5DGROParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, memory, params)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX5DGROParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, memory, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
