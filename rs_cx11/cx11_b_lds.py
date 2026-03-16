from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx11.common import (
    PROPOSAL_FEATURE_NAMES,
    load_base_params,
    predict_tree,
    proposal_context,
    fit_tree,
    tree_to_dict,
)


@dataclass(frozen=True)
class CX11BLDSParams:
    positive_gain: float
    max_depth: int
    prob_threshold: float
    min_gates: int
    max_overhead: float


DEFAULT_BASE = Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json')


def param_grid() -> list[CX11BLDSParams]:
    return [
        CX11BLDSParams(50.0, 2, 0.45, 1, 0.30),
        CX11BLDSParams(100.0, 2, 0.40, 1, 0.30),
        CX11BLDSParams(150.0, 3, 0.35, 1, 0.30),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'Always-Sketch', 'always_sketch': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX11BLDSParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    deps = dependencies or {}
    guard_cache = list(deps.get('guard_cache', []))
    base_memory = deps['base_memory']
    base_params = deps.get('base_params', load_base_params(DEFAULT_BASE))
    train_rows = [
        row for row in guard_cache
        if int(row.get('num_gates', 0)) >= int(params.min_gates)
    ]
    x = np.stack([np.asarray(r['proposal_feature'], dtype=np.float32) for r in train_rows], axis=0) if train_rows else np.zeros((0, len(PROPOSAL_FEATURE_NAMES)), dtype=np.float32)
    y = np.asarray([
        1 if float(r['exp_delta']) >= float(params.positive_gain) and float(r['success_delta']) >= 0.0 and float(r['time_overhead_ratio']) <= float(params.max_overhead) else 0
        for r in train_rows
    ], dtype=np.int64)
    tree = fit_tree(x, y, max_depth=int(params.max_depth)) if x.shape[0] > 0 else fit_tree(np.zeros((2, len(PROPOSAL_FEATURE_NAMES)), dtype=np.float32), np.asarray([0, 0], dtype=np.int64), max_depth=1)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'train_cases': int(len(train_rows)),
        'positive_cases': int(np.sum(y)) if y.size else 0,
        'feature_names': list(PROPOSAL_FEATURE_NAMES),
        'tree': tree_to_dict(tree, PROPOSAL_FEATURE_NAMES),
        'base_params': asdict(base_params),
    }
    (out_dir / 'lds_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'tree': tree,
        'train_rows': int(len(train_rows)),
        'positive_cases': int(np.sum(y)) if y.size else 0,
        'base_memory': base_memory,
        'base_params': base_params,
        'best_val_loss': float('nan'),
    }


class LDSPolicy:
    def __init__(self, base_policy) -> None:
        self.base_policy = base_policy

    def prepare_expand(self, *args, **kwargs):
        return self.base_policy.prepare_expand(*args, **kwargs)

    def rank_successors(self, *args, **kwargs):
        return self.base_policy.rank_successors(*args, **kwargs)


def _apply_overrides(params: CX11BLDSParams, overrides: dict[str, Any] | None) -> CX11BLDSParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def make_policy(memory: dict[str, Any], params: CX11BLDSParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    if isinstance(ablation, dict) and bool(ablation.get('always_sketch', False)):
        return cx10_d_las.make_policy(memory['base_memory'], memory['base_params'], case, bundle, field, device, ablation=None)
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    ctx = proposal_context(memory['base_memory'], memory['base_params'], case, bundle, field, device)
    if int(len(ctx['gates'])) < int(cur.min_gates):
        return None
    prob = float(predict_tree(memory['tree'], np.asarray(ctx['proposal_feature'], dtype=np.float32)))
    if prob < float(cur.prob_threshold):
        return None
    return LDSPolicy(ctx['base_policy'])


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX11BLDSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_nonholonomic_field(case, predictor, cfg, memory['base_params'] if memory else load_base_params(DEFAULT_BASE), memory['base_memory'] if memory else None)


def build_standard_field(sample, predictor, params: CX11BLDSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_standard_field(sample, predictor, memory['base_params'] if memory else load_base_params(DEFAULT_BASE), memory['base_memory'] if memory else None)
