from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import make_haa_policy
from rs_cx26.common import (
    DTOObservabilityMixin,
    DTO_SCHEMA,
    build_dto_compiler,
    compile_dto_contract_rows,
    build_frozen_cx25_stack,
    complete_dto_episode,
    dto_contract_meta,
    dto_evidence,
    init_dto_episode,
    macro_proxy_score,
)
from rs_cx23.common import apply_class_edit, class_key
from rs_cx23 import cx23_c_haa as haa_mod


@dataclass(frozen=True)
class CX26AHSTParams:
    occ_thr: float
    trans_thr: float
    dynamic_thr: float
    churn_thr: float
    loop_thr: float
    disagreement_thr: float
    budget_review: int
    budget_intervene: int
    commit_margin: float
    sibling_margin: float
    max_macros: int


def param_grid() -> list[CX26AHSTParams]:
    return [
        CX26AHSTParams(0.45, 0.45, 0.55, 0.25, 0.10, 0.55, 24, 12, 0.02, 0.01, 3),
        CX26AHSTParams(0.40, 0.40, 0.50, 0.20, 0.08, 0.50, 20, 10, 0.03, 0.02, 3),
        CX26AHSTParams(0.35, 0.35, 0.45, 0.18, 0.06, 0.45, 16, 8, 0.04, 0.02, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Hotspot-Trigger', 'disable_hst': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX26AHSTParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx25_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    dto_rows = compile_dto_contract_rows(
        calib_train_assets,
        stack,
        horizon_steps=int(stack.cx24_stack.haa_teacher.params.commit_steps + stack.cx24_stack.haa_teacher.params.recover_steps),
        stride=1,
    )
    compiler = build_dto_compiler(dto_rows, min_hits=4)
    meta = {'params': params.__dict__, 'dto_contract': dto_contract_meta(), 'compiler_keys': {'false_classes': compiler['false_ledger_classes'][:20], 'false_transitions': compiler['false_ledger_transitions'][:20]}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'hst_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'stack': stack, 'compiler': compiler, 'best_val_loss': float('nan')}


class HSTPolicy(DTOObservabilityMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX26AHSTParams, memory: dict[str, Any], disable_hst: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_hst = bool(disable_hst)
        self.stack = memory['stack']
        self.compiler = memory['compiler']
        self.inner = make_haa_policy(self.stack.cx24_stack.haa_teacher, case, bundle, self.field)
        self._dto_diag_init()

    def start_search(self, planner, start, goal, h_pair, search_state):
        init_dto_episode(search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        evidence = dto_evidence(self.compiler, ctx, search_state, self.case, self.bundle)
        evidence['dto_review_budget_left'] = float(max(int(self.params.budget_review) - int(search_state.get('dto_review_count', 0)), 0))
        evidence['dto_intervene_budget_left'] = float(max(int(self.params.budget_intervene) - int(search_state.get('dto_intervene_count', 0)), 0))
        ctx['dto_evidence'] = evidence
        self._dto_diag_record(record, search_state, ctx, evidence)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_hst or not isinstance(node_ctx, dict):
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if str(search_state.get('haa_state', 'observe')) != 'commit':
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        evidence = dict(node_ctx.get('dto_evidence', {}))
        gate1 = bool(
            float(evidence.get('occupancy_hotspot_score', 0.0)) >= float(self.params.occ_thr)
            or float(evidence.get('transition_hotspot_score', 0.0)) >= float(self.params.trans_thr)
            or float(evidence.get('false_commit_ledger_hit', 0.0)) >= 1.0
        )
        dynamic_terms = [
            float(evidence.get('churn_score', 0.0)) >= float(self.params.churn_thr),
            float(evidence.get('commit_recover_loop_score', 0.0)) >= float(self.params.loop_thr),
            float(evidence.get('local_proxy_disagreement', 0.0)) >= float(self.params.disagreement_thr),
        ]
        dynamic_count = int(sum(1 for x in dynamic_terms if bool(x)))
        dynamic_score = float(
            0.35 * float(evidence.get('churn_score', 0.0))
            + 0.30 * float(evidence.get('commit_recover_loop_score', 0.0))
            + 0.25 * float(evidence.get('local_proxy_disagreement', 0.0))
            + 0.10 * float(evidence.get('sibling_inconsistency', 0.0))
        )
        gate2 = bool(dynamic_count >= 2 and dynamic_score >= float(self.params.dynamic_thr))
        gate3 = bool(
            int(search_state.get('dto_review_count', 0)) < int(self.params.budget_review)
            and int(search_state.get('dto_intervene_count', 0)) < int(self.params.budget_intervene)
        )
        if not (gate1 and gate2 and gate3):
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        search_state['dto_review_count'] = int(search_state.get('dto_review_count', 0)) + 1
        current_key = str(class_key(node_ctx))
        commit_score, best_sib, sibling_score = macro_proxy_score(self.case, planner, record, h_pair, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, current_key, max_macros=int(self.params.max_macros))
        baseline_score = max((float(record.g + record.guided) - (record.g + float(c.guided)) for c in candidates if getattr(c, 'source', 'primitive') == 'primitive'), default=float('-inf'))
        fail_margin = max(baseline_score + float(self.params.commit_margin), sibling_score + float(self.params.sibling_margin))
        if commit_score < fail_margin:
            search_state['dto_intervene_count'] = int(search_state.get('dto_intervene_count', 0)) + 1
            edited = apply_class_edit(node_ctx, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
            node_ctx.clear(); node_ctx.update(edited)
            search_state['haa_state'] = 'recover'
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        complete_dto_episode(search_state, node_ctx if isinstance(node_ctx, dict) else None)


def make_policy(memory: dict[str, Any], params: CX26AHSTParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return HSTPolicy(case, bundle, field, params, memory, disable_hst=bool(ablation.get('disable_hst', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX26AHSTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].cx24_stack.haa_teacher.params, {'shadow_teacher': memory['stack'].cx24_stack.haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX26AHSTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].cx24_stack.haa_teacher.params, {'shadow_teacher': memory['stack'].cx24_stack.haa_teacher.shadow_teacher}).astype(np.float32)
