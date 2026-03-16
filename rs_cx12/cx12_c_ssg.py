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
    recent_anchor_progress,
    run_hybrid_with_policy,
    scene_context,
    tree_prob,
)


@dataclass(frozen=True)
class CX12CSSGParams:
    positive_gain: float
    negative_loss: float
    max_depth: int
    prob_threshold: float
    min_depth: int
    stall_progress_max: float
    near_gate_radius_m: float


def param_grid() -> list[CX12CSSGParams]:
    return [
        CX12CSSGParams(50.0, 50.0, 2, 0.45, 3, 0.12, 3.0),
        CX12CSSGParams(100.0, 50.0, 2, 0.40, 4, 0.10, 3.0),
        CX12CSSGParams(150.0, 100.0, 3, 0.35, 5, 0.08, 2.6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-State-Gate', 'disable_state_gate': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX12CSSGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
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
        rows.append({'feature': np.asarray(ctx['geom_feature'], dtype=np.float32), 'label': int(label)})
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
    (out_dir / 'ssg_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'tree': tree,
        'train_rows': int(len(rows)),
        'base_memory': base_memory,
        'base_params': base_params,
        'best_val_loss': float('nan'),
    }


class SSGPolicy:
    def __init__(self, case: dict[str, Any], field: np.ndarray, delegate, params: CX12CSSGParams, gate_state: tuple[float, float, float] | None) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.delegate = delegate
        self.params = params
        self.gate_state = gate_state

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        if self.delegate is None:
            return None
        if record.depth < int(self.params.min_depth):
            return {'mode': 0}
        stall = float(recent_anchor_progress(self.case, self.field, record, records, depth=3))
        near_gate = False
        if self.gate_state is not None:
            dx = float(record.x) - float(self.gate_state[0])
            dy = float(record.y) - float(self.gate_state[1])
            near_gate = float(np.hypot(dx, dy)) <= float(self.params.near_gate_radius_m)
        if (not bool(near_gate)) and stall > float(self.params.stall_progress_max):
            return {'mode': 0}
        return self.delegate.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.delegate is None:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        if mode == 0:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        return self.delegate.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX12CSSGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ctx = scene_context(memory['base_memory'], memory['base_params'], case, bundle, field, device)
    feat = np.asarray(ctx['geom_feature'], dtype=np.float32)
    prob = float(tree_prob(memory['tree'], feat))
    if prob < float(params.prob_threshold):
        return None
    delegate = ctx['base_policy']
    if isinstance(ablation, dict) and bool(ablation.get('disable_state_gate', False)):
        return delegate
    gate_state = tuple(float(v) for v in ctx['top_gate']['state']) if ctx['top_gate'] is not None else None
    return SSGPolicy(case, field, delegate, params, gate_state)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX12CSSGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_nonholonomic_field(case, predictor, cfg, memory['base_params'] if memory else load_base_params(BASE_CHOSEN_JSON), memory['base_memory'] if memory else None)


def build_standard_field(sample, predictor, params: CX12CSSGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_standard_field(sample, predictor, memory['base_params'] if memory else load_base_params(BASE_CHOSEN_JSON), memory['base_memory'] if memory else None)
