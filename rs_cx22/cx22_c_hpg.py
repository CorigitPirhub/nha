from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx22.common import (
    EPISODE_FEATURE_NAMES,
    build_frozen_teacher,
    episode_feature_vector,
    fit_tree,
    make_teacher_policy,
    predict_tree,
    teacher_case_deltas,
    teacher_prepare,
    tree_to_dict,
)
from rs_cx21 import cx21_b_lag as lag_mod


@dataclass(frozen=True)
class CX22CHPGParams:
    max_depth: int
    prob_thr: float
    min_exp_delta: float


def param_grid() -> list[CX22CHPGParams]:
    return [
        CX22CHPGParams(2, 0.55, 0.0),
        CX22CHPGParams(3, 0.60, 0.0),
        CX22CHPGParams(3, 0.70, 50.0),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Episode-Gate', 'disable_episode_gate': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX22CHPGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    case_rows = teacher_case_deltas(calib_train_assets, teacher, cap=20000)
    x = np.stack([np.asarray(row['episode_feature'], dtype=np.float32) for row in case_rows], axis=0)
    y = np.asarray([1 if float(row['success_delta']) >= 0.0 and float(row['exp_delta']) > float(params.min_exp_delta) else 0 for row in case_rows], dtype=np.int64)
    tree = fit_tree(x, y, max_depth=int(params.max_depth))
    lag_mod.save_meta(
        out_dir / 'hpg_meta.json',
        {
            'params': params.__dict__,
            'episode_tree': tree_to_dict(tree, EPISODE_FEATURE_NAMES),
            'case_rows': [{'sample_name': row['sample_name'], 'scenario': row['scenario'], 'exp_delta': row['exp_delta'], 'time_overhead_ratio': row['time_overhead_ratio']} for row in case_rows],
        },
    )
    return {'teacher': teacher, 'episode_tree': tree, 'best_val_loss': float('nan')}


class HPGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX22CHPGParams, memory: dict[str, Any], disable_episode_gate: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_episode_gate = bool(disable_episode_gate)
        self.teacher = memory['teacher']
        self.inner = make_teacher_policy(self.teacher, case, bundle, self.field)
        start_ctx = teacher_prepare(self.inner, tuple(map(float, case['start'])))
        feat = episode_feature_vector(case, bundle, start_ctx)
        prob = float(predict_tree(memory['episode_tree'], feat))
        self.active = bool(self.disable_episode_gate or prob >= float(self.params.prob_thr))
        self.episode_prob = float(prob)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        if not self.active:
            return {'active': False}
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict):
            ctx['episode_prob'] = float(self.episode_prob)
            ctx['active'] = True
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self.active:
            return []
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self.active:
            return None
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def should_run_hard(public_delta: list[dict[str, Any]], public_family: list[dict[str, Any]], method_name: str) -> bool:
    full = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == method_name), None)
    if full is None or float(full['success_delta_pp']) < 0.0 or float(full['exp_delta']) <= 0.0:
        return False
    family_map = {str(r['scenario']): float(r['exp_delta']) for r in public_family if r['dataset'] == 'exp4' and r['method'] == method_name}
    margin = float(full['exp_delta']) + 0.75 * min(0.0, float(family_map.get('narrow_passage', 0.0))) + 0.75 * min(0.0, float(family_map.get('maze', 0.0))) + 0.50 * min(0.0, float(family_map.get('parasol_misc', 0.0)))
    return bool(float(margin) > 0.0 and float(family_map.get('flange', -1.0)) >= 0.0)


def make_policy(memory: dict[str, Any], params: CX22CHPGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return HPGPolicy(case, bundle, field, params, memory, disable_episode_gate=bool(ablation.get('disable_episode_gate', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX22CHPGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = lag_mod.build_nonholonomic_field(case, predictor, cfg, memory['teacher'].params, memory['teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX22CHPGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return lag_mod.build_standard_field(sample, predictor, memory['teacher'].params, memory['teacher'].memory).astype(np.float32)
