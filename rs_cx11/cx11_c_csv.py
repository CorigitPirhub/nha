from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx11.common import (
    TOKEN_FEATURE_NAMES,
    SupportBand,
    best_mode_progress,
    fit_support_band,
    load_base_params,
    proposal_context,
    support_match,
    token_key,
)


@dataclass(frozen=True)
class CX11CCSVParams:
    min_asset_gain: float
    low_q: float
    high_q: float
    sim_q: float
    slack: float
    min_token_count: int


DEFAULT_BASE = Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json')


def param_grid() -> list[CX11CCSVParams]:
    return [
        CX11CCSVParams(50.0, 0.10, 0.90, 0.20, 0.05, 2),
        CX11CCSVParams(100.0, 0.15, 0.85, 0.25, 0.04, 2),
        CX11CCSVParams(150.0, 0.20, 0.80, 0.30, 0.03, 1),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Verify', 'always_sketch': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX11CCSVParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    deps = dependencies or {}
    guard_cache = list(deps.get('guard_cache', []))
    base_memory = deps['base_memory']
    base_params = deps.get('base_params', load_base_params(DEFAULT_BASE))
    token_bank: dict[str, SupportBand] = {}
    token_rows: dict[str, list[np.ndarray]] = {}
    token_progress: dict[str, list[float]] = {}
    for row in guard_cache:
        if float(row['exp_delta']) < float(params.min_asset_gain) or float(row['success_delta']) < 0.0:
            continue
        for gate in row.get('gate_rows', []):
            key = str(gate['token_key'])
            token_rows.setdefault(key, []).append(np.asarray(gate['token_feature'], dtype=np.float32))
            token_progress.setdefault(key, []).append(float(gate.get('mode_progress', 0.0)))
    for key, feats in token_rows.items():
        if len(feats) < int(params.min_token_count):
            continue
        band = fit_support_band(feats, token_progress.get(key, []), low_q=float(params.low_q), high_q=float(params.high_q), sim_q=float(params.sim_q))
        if band is not None:
            token_bank[key] = band
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'token_counts': {k: int(len(v)) for k, v in token_rows.items()},
        'fit_keys': sorted(token_bank.keys()),
        'base_params': asdict(base_params),
    }
    (out_dir / 'csv_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'token_bank': token_bank,
        'train_rows': int(sum(len(v) for v in token_rows.values())),
        'base_memory': base_memory,
        'base_params': base_params,
        'best_val_loss': float('nan'),
    }


class CSVPolicy(cx10_d_las.LASPolicy):
    pass


def _apply_overrides(params: CX11CCSVParams, overrides: dict[str, Any] | None) -> CX11CCSVParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def make_policy(memory: dict[str, Any], params: CX11CCSVParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    if isinstance(ablation, dict) and bool(ablation.get('always_sketch', False)):
        return cx10_d_las.make_policy(memory['base_memory'], memory['base_params'], case, bundle, field, device, ablation=None)
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    ctx = proposal_context(memory['base_memory'], memory['base_params'], case, bundle, field, device)
    kept = []
    for gate in ctx['gates']:
        key = str(gate['token_key'])
        band = memory['token_bank'].get(key, None)
        progress_inner = best_mode_progress(case, field, gate['state'], int(gate.get('inner_mode', 0)))
        progress_outer = best_mode_progress(case, field, gate['state'], int(gate.get('outer_mode', 0))) if int(gate.get('outer_mode', 0)) > 0 else -1e6
        progress = max(float(progress_inner), float(progress_outer))
        ok, sim = support_match(band, np.asarray(gate['token_feature'], dtype=np.float32), float(progress), slack=float(cur.slack))
        if ok:
            kept.append({**gate, 'score': float(max(gate['score'], sim))})
    if not kept:
        return None
    return CSVPolicy(case, kept, memory['base_params'])


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX11CCSVParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_nonholonomic_field(case, predictor, cfg, memory['base_params'] if memory else load_base_params(DEFAULT_BASE), memory['base_memory'] if memory else None)


def build_standard_field(sample, predictor, params: CX11CCSVParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_standard_field(sample, predictor, memory['base_params'] if memory else load_base_params(DEFAULT_BASE), memory['base_memory'] if memory else None)
