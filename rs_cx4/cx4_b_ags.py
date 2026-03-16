from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard, patch_similarity, sparse_patch_from_hotspots
from rs_cx.common import CXGlobalConfig
from scripts.evaluate_baselines import _make_rs_anchor, _run_hybrid_method


@dataclass(frozen=True)
class CX4BAGSParams:
    gain: float
    sim_temp: float
    top_quantile: float


def param_grid() -> list[CX4BAGSParams]:
    return [
        CX4BAGSParams(0.60, 3.0, 0.985),
        CX4BAGSParams(0.80, 4.0, 0.987),
        CX4BAGSParams(1.00, 5.0, 0.990),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg: CXGlobalConfig, params: CX4BAGSParams) -> dict[str, Any]:
    proto = []
    for item in dev_cases:
        bundle, field = accepted_cx3d_nonholonomic(item['case'], predictor, cfg)
        cx = _run_hybrid_method(item['case'], _make_rs_anchor(item['case'], rs_field=field), max_expansions=7000)
        baseline = item.get('cx3d', cx)
        gap = float(baseline['expansions']) - float(cx['expansions'])
        if gap <= 0.0:
            continue
        proto.append({'scene': dict(bundle['scene']), 'patch': sparse_patch_from_hotspots(bundle, item['case']['occupancy'], params.top_quantile)})
    return {'proto': proto}


def _blend_patch(bundle: dict, memory: dict[str, Any], params: CX4BAGSParams) -> np.ndarray:
    if not memory['proto']:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    sims = np.asarray([patch_similarity(bundle, p['scene']) for p in memory['proto']], dtype=np.float32)
    if float(np.max(sims)) <= 1e-8:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    weights = np.exp(float(params.sim_temp) * sims)
    weights = weights / max(float(np.sum(weights)), 1e-6)
    out = np.zeros_like(bundle['focus'], dtype=np.float32)
    for w, p in zip(weights, memory['proto']):
        out += float(w) * np.asarray(p['patch'], dtype=np.float32)
    return out


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX4BAGSParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    patch = _blend_patch(bundle, memory, params)
    out = np.clip(field + float(params.gain) * patch[None, ...] * bundle['focus'][None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX4BAGSParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_cx3d_standard(sample, predictor)
    patch = _blend_patch(bundle, memory, params)
    out = np.clip(field + float(params.gain) * patch * bundle['focus'], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
