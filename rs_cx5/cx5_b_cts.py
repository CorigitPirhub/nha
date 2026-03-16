from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage

from config import DEFAULT_CONFIG
from rs_cx5.common import accepted_bundle_nonholonomic, accepted_bundle_standard, culprit_funnel_map, dev_trace_memory, trace_similarity


@dataclass(frozen=True)
class CX5BCTSParams:
    gain: float
    sim_temp: float
    top_quantile: float


def param_grid() -> list[CX5BCTSParams]:
    return [
        CX5BCTSParams(0.60, 3.0, 0.985),
        CX5BCTSParams(0.80, 4.0, 0.987),
        CX5BCTSParams(1.00, 5.0, 0.990),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg, params: CX5BCTSParams) -> dict[str, Any]:
    return dev_trace_memory(dev_cases, predictor, cfg)


def _resize_patch(arr: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
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


def _blend(bundle: dict, memory: dict[str, Any], params: CX5BCTSParams) -> np.ndarray:
    if not memory['proto']:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    sims = np.asarray([trace_similarity(bundle, p['scene']) for p in memory['proto']], dtype=np.float32)
    if float(np.max(sims)) <= 1e-8:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    weights = np.exp(float(params.sim_temp) * sims)
    weights = weights / max(float(np.sum(weights)), 1e-6)
    out = np.zeros_like(bundle['focus'], dtype=np.float32)
    for w, p in zip(weights, memory['proto']):
        patch = _resize_patch(np.asarray(p['funnel'], dtype=np.float32), out.shape)
        out += float(w) * patch
    return out


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX5BCTSParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    funnel = culprit_funnel_map(bundle, case['occupancy'])
    proto = _blend(bundle, memory, params)
    delta = float(params.gain) * 0.5 * (funnel + proto)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX5BCTSParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    funnel = culprit_funnel_map(bundle, sample.occupancy)
    proto = _blend(bundle, memory, params)
    delta = float(params.gain) * 0.5 * (funnel + proto)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
