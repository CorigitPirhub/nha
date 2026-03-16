from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx6.common import accepted_bundle_nonholonomic, accepted_bundle_standard, culprit_replay_map, resize_like


@dataclass(frozen=True)
class CX6BCRLParams:
    gain: float
    sim_temp: float


def param_grid() -> list[CX6BCRLParams]:
    return [
        CX6BCRLParams(0.50, 2.0),
        CX6BCRLParams(0.70, 3.0),
        CX6BCRLParams(0.90, 4.0),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg, params: CX6BCRLParams) -> dict[str, Any]:
    proto=[]
    for item in dev_cases:
        bundle,_ = accepted_bundle_nonholonomic(item['case'], predictor, cfg)
        proto.append({'scene': dict(bundle['scene']), 'replay': culprit_replay_map(bundle)})
    return {'proto': proto}


def _blend(bundle: dict, memory: dict[str, Any], params: CX6BCRLParams) -> np.ndarray:
    if not memory['proto']:
        return np.zeros_like(bundle['focus'])
    sims=[]
    for p in memory['proto']:
        s=bundle['scene']; t=p['scene']
        diff=abs(float(s.get('hard_likelihood',0.0))-float(t.get('hard_likelihood',0.0)))+abs(float(s.get('misc_likelihood',0.0))-float(t.get('misc_likelihood',0.0)))
        sims.append(np.exp(-3.0*diff))
    sims=np.asarray(sims,dtype=np.float32)
    w=np.exp(float(params.sim_temp)*sims); w=w/max(float(np.sum(w)),1e-6)
    out=np.zeros_like(bundle['focus'],dtype=np.float32)
    for wi,p in zip(w,memory['proto']):
        out += float(wi)*resize_like(np.asarray(p['replay'],dtype=np.float32), out.shape)
    return out


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX6BCRLParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    replay = culprit_replay_map(bundle)
    proto = _blend(bundle, memory, params)
    delta = float(params.gain) * 0.5 * (replay + proto)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX6BCRLParams, memory: dict[str, Any]) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    replay = culprit_replay_map(bundle)
    proto = _blend(bundle, memory, params)
    delta = float(params.gain) * 0.5 * (replay + proto)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
