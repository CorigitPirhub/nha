from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin
from rs_cx25.common import (
    build_frozen_cx24_stack,
    build_positive_negative_support,
    class_key,
    compile_dto_rows,
    compile_risk_hotspots,
    compile_transition_hotspots,
    make_ato_policy,
    policy_prepare,
)
from rs_cx23 import cx23_c_haa as haa_mod


@dataclass(frozen=True)
class CX25BDTOParams:
    min_hits: int
    trace_stride: int


def param_grid() -> list[CX25BDTOParams]:
    return [
        CX25BDTOParams(3, 1),
        CX25BDTOParams(4, 1),
        CX25BDTOParams(5, 1),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Compiler', 'disable_compiler': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX25BDTOParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx24_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_dto_rows(calib_train_assets, stack, horizon_steps=int(stack.haa_teacher.params.commit_steps + stack.haa_teacher.params.recover_steps), stride=int(params.trace_stride))
    risk_hotspots = compile_risk_hotspots(rows, min_hits=int(params.min_hits))
    transition_hotspots = compile_transition_hotspots(rows, min_hits=int(params.min_hits))
    pos_support, neg_support = build_positive_negative_support(rows, min_hits=int(params.min_hits))
    haa_mod.base_mod.lag_mod.save_meta(
        out_dir / 'dto_meta.json',
        {
            'params': params.__dict__,
            'risk_hotspots': risk_hotspots,
            'transition_hotspots': transition_hotspots,
            'positive_classes': sorted(pos_support.keys()),
            'negative_classes': sorted(neg_support.keys()),
        },
    )
    return {'stack': stack, 'risk_hotspots': risk_hotspots, 'transition_hotspots': transition_hotspots, 'pos_support': pos_support, 'neg_support': neg_support, 'best_val_loss': float('nan')}


class DTOPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX25BDTOParams, memory: dict[str, Any], disable_compiler: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_compiler = bool(disable_compiler)
        self.stack = memory['stack']
        self.inner = make_ato_policy(self.stack, case, bundle, self.field)
        self.risk_hotspots = dict(memory.get('risk_hotspots', {}))
        self.transition_hotspots = dict(memory.get('transition_hotspots', {}))
        self._diag_init()

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state['dto_prev_auto'] = 'observe'
        search_state['dto_prev_class'] = 'uncertain|none'

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict) and not self.disable_compiler:
            ckey = str(class_key(ctx))
            trans = f"{search_state.get('dto_prev_auto','observe')}->{search_state.get('haa_state','observe')}"
            ctx['dto_risk_score'] = float(self.risk_hotspots.get(ckey, {}).get('neg_rate', 0.0))
            ctx['dto_transition_risk'] = float(self.transition_hotspots.get(trans, {}).get('neg_rate', 0.0))
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        search_state['dto_prev_auto'] = str(search_state.get('haa_state', 'observe'))
        if isinstance(node_ctx, dict):
            search_state['dto_prev_class'] = str(class_key(node_ctx))

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX25BDTOParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return DTOPolicy(case, bundle, field, params, memory, disable_compiler=bool(ablation.get('disable_compiler', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX25BDTOParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX25BDTOParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher}).astype(np.float32)
