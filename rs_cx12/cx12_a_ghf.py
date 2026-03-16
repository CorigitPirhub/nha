from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx12.common import (
    BASE_CHOSEN_JSON,
    GEOM_FEATURE_NAMES,
    compare_plan_to_baseline,
    fit_geom_tree,
    geom_tree_dict,
    load_base_params,
    run_hybrid_with_policy,
    scene_context,
    standard_identity_error,
    tree_prob,
)


@dataclass(frozen=True)
class CX12AGHFParams:
    positive_gain: float
    negative_loss: float
    max_depth: int
    prob_threshold: float
    goal_ray_min: float
    trap_score_max: float


def param_grid() -> list[CX12AGHFParams]:
    return [
        CX12AGHFParams(50.0, 50.0, 2, 0.45, 0.8, 3.0),
        CX12AGHFParams(100.0, 50.0, 2, 0.40, 0.8, 3.5),
        CX12AGHFParams(150.0, 100.0, 3, 0.35, 1.0, 3.5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Hard-Filter', 'always_sketch': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX12AGHFParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    deps = dependencies or {}
    guard_assets = list(deps.get('guard_assets', []))
    base_memory = deps['base_memory']
    base_params = deps.get('base_params', load_base_params(BASE_CHOSEN_JSON))
    rows = []
    for asset in guard_assets:
        ctx = scene_context(base_memory, base_params, asset['case'], asset['bundle'], asset['field'], device)
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(deps.get('dev_cap', 20000)), successor_policy=ctx['base_policy'], record_expanded=False) if ctx['base_policy'] is not None else asset['baseline_result']
        delta = compare_plan_to_baseline(asset['baseline_result'], plan, prep_ms=0.0)
        label = 0
        if str(asset['case']['scenario']) == 'narrow_passage' and float(delta['exp_delta']) >= float(params.positive_gain):
            label = 1
        elif str(asset['case']['scenario']) == 'flange' and float(delta['exp_delta']) <= -float(params.negative_loss):
            label = 0
        else:
            continue
        rows.append({
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'feature': np.asarray(ctx['geom_feature'], dtype=np.float32),
            'label': int(label),
            'exp_delta': float(delta['exp_delta']),
        })
    x = np.stack([np.asarray(r['feature'], dtype=np.float32) for r in rows], axis=0) if rows else np.zeros((2, len(GEOM_FEATURE_NAMES)), dtype=np.float32)
    y = np.asarray([int(r['label']) for r in rows], dtype=np.int64) if rows else np.asarray([0, 0], dtype=np.int64)
    tree = fit_geom_tree(x, y, int(params.max_depth))
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'train_rows': int(len(rows)),
        'positive_rows': int(np.sum(y)),
        'feature_names': list(GEOM_FEATURE_NAMES),
        'tree': geom_tree_dict(tree),
        'base_params': asdict(base_params),
    }
    (out_dir / 'ghf_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'tree': tree,
        'train_rows': int(len(rows)),
        'base_memory': base_memory,
        'base_params': base_params,
        'best_val_loss': float('nan'),
    }


class GHFPolicy:
    def __init__(self, delegate) -> None:
        self.delegate = delegate

    def prepare_expand(self, *args, **kwargs):
        return self.delegate.prepare_expand(*args, **kwargs)

    def rank_successors(self, *args, **kwargs):
        return self.delegate.rank_successors(*args, **kwargs)


def make_policy(memory: dict[str, Any], params: CX12AGHFParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    if isinstance(ablation, dict) and bool(ablation.get('always_sketch', False)):
        return cx10_d_las.make_policy(memory['base_memory'], memory['base_params'], case, bundle, field, device, ablation=None)
    ctx = scene_context(memory['base_memory'], memory['base_params'], case, bundle, field, device)
    feat = np.asarray(ctx['geom_feature'], dtype=np.float32)
    prob = float(tree_prob(memory['tree'], feat))
    goal_ray = float(feat[GEOM_FEATURE_NAMES.index('goal_ray_len')])
    trap_score = float(feat[GEOM_FEATURE_NAMES.index('trap_score')])
    if prob < float(params.prob_threshold):
        return None
    if goal_ray < float(params.goal_ray_min):
        return None
    if trap_score > float(params.trap_score_max):
        return None
    return GHFPolicy(ctx['base_policy']) if ctx['base_policy'] is not None else None


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX12AGHFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_nonholonomic_field(case, predictor, cfg, memory['base_params'] if memory else load_base_params(BASE_CHOSEN_JSON), memory['base_memory'] if memory else None)


def build_standard_field(sample, predictor, params: CX12AGHFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_standard_field(sample, predictor, memory['base_params'] if memory else load_base_params(BASE_CHOSEN_JSON), memory['base_memory'] if memory else None)
