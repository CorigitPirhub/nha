from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, build_state_support, compile_haa_trace_rows, trace_feature_vector
from rs_cx25.common import best_support_class, build_frozen_cx24_stack, make_ato_policy, soft_downgrade_ctx
from rs_cx23 import cx23_c_haa as haa_mod


@dataclass(frozen=True)
class CX25DTSDParams:
    min_hits: int
    support_slack: float
    max_macros: int


def param_grid() -> list[CX25DTSDParams]:
    return [
        CX25DTSDParams(3, 0.22, 3),
        CX25DTSDParams(4, 0.20, 3),
        CX25DTSDParams(5, 0.18, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Tail-Downgrade', 'disable_tail_downgrade': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX25DTSDParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx24_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_haa_trace_rows(calib_train_assets, stack.haa_teacher, horizon_steps=int(stack.haa_teacher.params.commit_steps + stack.haa_teacher.params.recover_steps), stride=1)
    tail_support = build_state_support(rows, predicate=lambda r: float(r['future_gain']) <= 0.0 and (int(r['support_count']) <= 1 or int(r['recover_left']) > 0), min_hits=int(params.min_hits))
    haa_mod.base_mod.lag_mod.save_meta(out_dir / 'tsd_meta.json', {'params': params.__dict__, 'tail_keys': sorted(tail_support.keys())})
    return {'stack': stack, 'tail_support': tail_support, 'best_val_loss': float('nan')}


class TSDPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX25DTSDParams, memory: dict[str, Any], disable_tail_downgrade: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_tail_downgrade = bool(disable_tail_downgrade)
        self.stack = memory['stack']
        self.inner = make_ato_policy(self.stack, case, bundle, self.field)
        self.tail_support = dict(memory.get('tail_support', {}))
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict) and (not self.disable_tail_downgrade):
            feat = trace_feature_vector(ctx, search_state, self.case, self.bundle)
            key, sim = best_support_class(self.tail_support, feat, gain_hint=float(ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
            if key != 'uncertain|none' and str(search_state.get('haa_state', 'observe')) == 'commit':
                ctx = soft_downgrade_ctx(ctx, self.stack.haa_teacher.shadow_teacher.lag_teacher, max_macros=int(self.params.max_macros), mode='tail_soft')
                search_state['haa_support_count'] = max(int(search_state.get('haa_support_count', 0)) - 1, 0)
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX25DTSDParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return TSDPolicy(case, bundle, field, params, memory, disable_tail_downgrade=bool(ablation.get('disable_tail_downgrade', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX25DTSDParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX25DTSDParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher}).astype(np.float32)
