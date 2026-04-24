from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_macro_rescue.stack.base import CXGlobalConfig
from rs_macro_rescue.stack.haa import apply_class_edit, build_frozen_shadow_teacher, class_key, compile_shadow_rows, make_shadow_policy, shadow_prepare
from rs_macro_rescue.stack import shadow_policy as base_mod


@dataclass(frozen=True)
class CX23CHAAParams:
    min_hits: int
    min_gain: float
    commit_steps: int
    recover_steps: int
    max_macros: int


def param_grid() -> list[CX23CHAAParams]:
    return [
        CX23CHAAParams(3, 0.00, 2, 3, 3),
        CX23CHAAParams(4, 0.02, 2, 4, 3),
        CX23CHAAParams(4, 0.05, 3, 4, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Automaton', 'disable_automaton': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX23CHAAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    shadow_teacher = build_frozen_shadow_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_shadow_rows(calib_train_assets, shadow_teacher, horizon_steps=int(shadow_teacher.lag_teacher.params.horizon_steps), stride=1)
    stats = {}
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), []).append(float(row['future_gain']))
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        if int(arr.size) >= int(params.min_hits):
            stats[str(key)] = {'avg_gain': float(np.mean(arr)), 'hits': int(arr.size)}
    base_mod.lag_mod.save_meta(out_dir / 'haa_meta.json', {'params': params.__dict__, 'class_stats': stats})
    return {'shadow_teacher': shadow_teacher, 'class_stats': stats, 'best_val_loss': float('nan')}


class HAAPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX23CHAAParams, memory: dict[str, Any], disable_automaton: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_automaton = bool(disable_automaton)
        self.shadow_teacher = memory['shadow_teacher']
        self.inner = make_shadow_policy(self.shadow_teacher, case, bundle, self.field)
        self.class_stats = dict(memory.get('class_stats', {}))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = shadow_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        if self.disable_automaton:
            return ctx
        key = str(class_key(ctx))
        stat = self.class_stats.get(key, {'avg_gain': 0.0, 'hits': 0})
        state = str(search_state.get('haa_state', 'observe'))
        cur_key = str(search_state.get('haa_key', ''))
        support_count = int(search_state.get('haa_support_count', 0))
        recover_left = int(search_state.get('haa_recover_left', 0))
        supportive = bool(float(stat.get('avg_gain', 0.0)) >= float(self.params.min_gain))
        if state == 'recover':
            recover_left = max(recover_left - 1, 0)
            if recover_left <= 0:
                state = 'observe'
        if state == 'observe':
            if supportive:
                state = 'candidate'
                cur_key = key
                support_count = 1
        elif state == 'candidate':
            if supportive and key == cur_key:
                support_count += 1
                if support_count >= int(self.params.commit_steps):
                    state = 'commit'
            else:
                state = 'observe'
                support_count = 0
                cur_key = ''
        elif state == 'commit':
            if (not supportive) or key != cur_key:
                state = 'recover'
                recover_left = int(self.params.recover_steps)
        search_state['haa_state'] = state
        search_state['haa_key'] = cur_key
        search_state['haa_support_count'] = int(support_count)
        search_state['haa_recover_left'] = int(recover_left)
        if state != 'commit':
            return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
        return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, cur_key, max_macros=int(self.params.max_macros))

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX23CHAAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return HAAPolicy(case, bundle, field, params, memory, disable_automaton=bool(ablation.get('disable_automaton', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX23CHAAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, memory['shadow_teacher'].params, memory['shadow_teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX23CHAAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_standard_field(sample, predictor, memory['shadow_teacher'].params, memory['shadow_teacher'].memory).astype(np.float32)
