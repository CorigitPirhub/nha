from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx11.common import SupportBand, fit_support_band, load_base_params, proposal_context, token_key


@dataclass(frozen=True)
class CX11ARSTParams:
    min_asset_gain: float
    low_q: float
    high_q: float
    sim_q: float
    slack: float
    similarity_threshold: float
    min_type_count: int


DEFAULT_BASE = Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json')


def param_grid() -> list[CX11ARSTParams]:
    return [
        CX11ARSTParams(50.0, 0.10, 0.90, 0.20, 0.05, 0.70, 2),
        CX11ARSTParams(100.0, 0.15, 0.85, 0.25, 0.04, 0.75, 2),
        CX11ARSTParams(150.0, 0.20, 0.80, 0.30, 0.03, 0.80, 1),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Typed-Guard', 'always_sketch': True},
    ]


def _typed_key(base_key: str, corridor: float, threshold: float) -> str:
    return f'{base_key}|{"tight" if float(corridor) <= float(threshold) else "wide"}'


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX11ARSTParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    deps = dependencies or {}
    guard_cache = list(deps.get('guard_cache', []))
    base_memory = deps['base_memory']
    base_params = deps.get('base_params', load_base_params(DEFAULT_BASE))
    corridor_values: dict[str, list[float]] = {}
    positive_rows = []
    for row in guard_cache:
        if float(row['exp_delta']) < float(params.min_asset_gain) or float(row['success_delta']) < 0.0:
            continue
        for gate in row.get('gate_rows', []):
            base_key = str(gate['token_key'])
            corridor_values.setdefault(base_key, []).append(float(gate['token_feature'][8]))
            positive_rows.append(gate)
    medians = {k: float(np.median(v)) for k, v in corridor_values.items() if len(v) > 0}
    grouped: dict[str, list[np.ndarray]] = {}
    for gate in positive_rows:
        base_key = str(gate['token_key'])
        thr = medians.get(base_key, float(gate['token_feature'][8]))
        tkey = _typed_key(base_key, float(gate['token_feature'][8]), thr)
        grouped.setdefault(tkey, []).append(np.asarray(gate['token_feature'], dtype=np.float32))
    type_bank: dict[str, SupportBand] = {}
    for key, feats in grouped.items():
        if len(feats) < int(params.min_type_count):
            continue
        band = fit_support_band(feats, [0.0] * len(feats), low_q=float(params.low_q), high_q=float(params.high_q), sim_q=float(params.sim_q))
        if band is not None:
            type_bank[key] = band
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'typed_counts': {k: int(len(v)) for k, v in grouped.items()},
        'corridor_medians': medians,
        'type_keys': sorted(type_bank.keys()),
        'base_params': asdict(base_params),
    }
    (out_dir / 'rst_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'type_bank': type_bank,
        'corridor_medians': medians,
        'train_rows': int(sum(len(v) for v in grouped.values())),
        'base_memory': base_memory,
        'base_params': base_params,
        'best_val_loss': float('nan'),
    }


class RSTPolicy(cx10_d_las.LASPolicy):
    pass


def _apply_overrides(params: CX11ARSTParams, overrides: dict[str, Any] | None) -> CX11ARSTParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def _match_typed_gate(memory: dict[str, Any], gate: dict[str, Any], params: CX11ARSTParams) -> tuple[bool, float]:
    base_key = str(gate['token_key'])
    thr = float(memory['corridor_medians'].get(base_key, float(gate['token_feature'][8])))
    tkey = _typed_key(base_key, float(gate['token_feature'][8]), thr)
    band = memory['type_bank'].get(tkey, None)
    if band is None:
        return False, 0.0
    feat = np.asarray(gate['token_feature'], dtype=np.float32)
    low = np.asarray(band.low, dtype=np.float32) - float(params.slack)
    high = np.asarray(band.high, dtype=np.float32) + float(params.slack)
    within = np.all((feat >= low) & (feat <= high))
    dim = feat.shape[0]
    mean = np.asarray(band.prototype[:dim], dtype=np.float32)
    std = np.asarray(band.prototype[dim:2 * dim], dtype=np.float32)
    proto = np.asarray(band.prototype[2 * dim:], dtype=np.float32)
    z = (feat - mean) / std
    zn = float(np.linalg.norm(z))
    if zn > 1e-6:
        z = z / zn
    sim = float(np.dot(z.astype(np.float32), proto.astype(np.float32)))
    return bool(within and sim >= float(max(params.similarity_threshold, band.similarity_floor))), float(sim)


def make_policy(memory: dict[str, Any], params: CX11ARSTParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    if isinstance(ablation, dict) and bool(ablation.get('always_sketch', False)):
        return cx10_d_las.make_policy(memory['base_memory'], memory['base_params'], case, bundle, field, device, ablation=None)
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    ctx = proposal_context(memory['base_memory'], memory['base_params'], case, bundle, field, device)
    kept = []
    for gate in ctx['gates']:
        ok, sim = _match_typed_gate(memory, gate, cur)
        if ok:
            kept.append({**gate, 'score': float(max(gate['score'], sim))})
    if not kept:
        return None
    return RSTPolicy(case, kept, memory['base_params'])


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX11ARSTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_nonholonomic_field(case, predictor, cfg, memory['base_params'] if memory else load_base_params(DEFAULT_BASE), memory['base_memory'] if memory else None)


def build_standard_field(sample, predictor, params: CX11ARSTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_standard_field(sample, predictor, memory['base_params'] if memory else load_base_params(DEFAULT_BASE), memory['base_memory'] if memory else None)
