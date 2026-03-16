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
    class_parts,
    compile_dto_rows,
    compile_risk_hotspots,
    compile_transition_hotspots,
    make_ccc_policy,
    soft_downgrade_ctx,
)
from rs_cx23 import cx23_c_haa as haa_mod
from rs_cx23.common import apply_class_edit


@dataclass(frozen=True)
class CX25ASSCParams:
    min_hits: int
    risk_thr: float
    transition_thr: float
    oscillation_thr: int
    commit_margin: float
    sibling_margin: float
    max_macros: int


def param_grid() -> list[CX25ASSCParams]:
    return [
        CX25ASSCParams(3, 0.40, 0.40, 1, 0.02, 0.01, 3),
        CX25ASSCParams(4, 0.35, 0.35, 1, 0.03, 0.02, 3),
        CX25ASSCParams(4, 0.30, 0.30, 2, 0.04, 0.02, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Selective-Soft', 'disable_selective_soft': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX25ASSCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx24_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_dto_rows(calib_train_assets, stack, horizon_steps=int(stack.haa_teacher.params.commit_steps + stack.haa_teacher.params.recover_steps), stride=1)
    risk_hotspots = compile_risk_hotspots(rows, min_hits=int(params.min_hits))
    transition_hotspots = compile_transition_hotspots(rows, min_hits=int(params.min_hits))
    pos_support, neg_support = build_positive_negative_support(rows, min_hits=int(params.min_hits))
    haa_mod.base_mod.lag_mod.save_meta(out_dir / 'ssc_meta.json', {'params': params.__dict__, 'risk_hotspots': risk_hotspots, 'transition_hotspots': transition_hotspots})
    return {'stack': stack, 'risk_hotspots': risk_hotspots, 'transition_hotspots': transition_hotspots, 'pos_support': pos_support, 'neg_support': neg_support, 'best_val_loss': float('nan')}


class SSCPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX25ASSCParams, memory: dict[str, Any], disable_selective_soft: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_selective_soft = bool(disable_selective_soft)
        self.stack = memory['stack']
        self.inner = make_ccc_policy(self.stack, case, bundle, self.field)
        self.risk_hotspots = dict(memory.get('risk_hotspots', {}))
        self.transition_hotspots = dict(memory.get('transition_hotspots', {}))
        self._diag_init()

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state['ssc_prev_auto'] = 'observe'
        search_state['ssc_commit_recover_osc'] = 0

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        if self.disable_selective_soft:
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
            return ctx
        ckey = str(class_key(ctx))
        auto_state = str(search_state.get('haa_state', 'observe'))
        prev_auto = str(search_state.get('ssc_prev_auto', 'observe'))
        if prev_auto == 'commit' and auto_state == 'recover':
            search_state['ssc_commit_recover_osc'] = int(search_state.get('ssc_commit_recover_osc', 0)) + 1
        risk_score = float(self.risk_hotspots.get(ckey, {}).get('neg_rate', 0.0))
        trans_score = float(self.transition_hotspots.get(f'{prev_auto}->{auto_state}', {}).get('neg_rate', 0.0))
        high_risk = bool(
            auto_state == 'commit'
            and (
                risk_score >= float(self.params.risk_thr)
                or trans_score >= float(self.params.transition_thr)
                or int(search_state.get('ssc_commit_recover_osc', 0)) >= int(self.params.oscillation_thr)
            )
        )
        ctx['ssc_high_risk'] = bool(high_risk)
        self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_selective_soft or not isinstance(node_ctx, dict) or not bool(node_ctx.get('ssc_high_risk', False)):
            return extra
        current_key = str(class_key(node_ctx))
        mode, bucket = class_parts(current_key)
        commit_score = self.inner._macro_proxy_score(planner, record, h_pair, mode, bucket)
        baseline_score = max((float(record.g + record.guided) - (record.g + float(c.guided)) for c in candidates if getattr(c, 'source', 'primitive') == 'primitive'), default=float('-inf'))
        siblings = [b for b in ('straight', 'forward_turn', 'reverse', 'reverse_setup') if b != str(bucket)]
        sibling_scores = [(sib, self.inner._macro_proxy_score(planner, record, h_pair, mode, sib)) for sib in siblings]
        sib, sibling_score = max(sibling_scores, key=lambda item: item[1], default=('none', float('-inf')))
        fail_margin = max(baseline_score + float(self.params.commit_margin), sibling_score + float(self.params.sibling_margin))
        if commit_score < fail_margin:
            if sibling_score > baseline_score + float(self.params.sibling_margin):
                edited = apply_class_edit(node_ctx, self.stack.haa_teacher.shadow_teacher.lag_teacher, f'{mode}|{sib}', max_macros=int(self.params.max_macros))
            else:
                edited = soft_downgrade_ctx(node_ctx, self.stack.haa_teacher.shadow_teacher.lag_teacher, max_macros=int(self.params.max_macros))
            node_ctx.clear()
            node_ctx.update(edited)
            search_state['haa_state'] = 'candidate'
            search_state['haa_support_count'] = max(int(self.stack.haa_teacher.params.commit_steps) - 1, 1)
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        return extra

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        search_state['ssc_prev_auto'] = str(search_state.get('haa_state', 'observe'))


def make_policy(memory: dict[str, Any], params: CX25ASSCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SSCPolicy(case, bundle, field, params, memory, disable_selective_soft=bool(ablation.get('disable_selective_soft', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX25ASSCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX25ASSCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher}).astype(np.float32)
