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
    build_dto_compiler,
    compile_dto_contract_rows,
    build_frozen_cx25_stack,
    complete_dto_episode,
    dto_contract_meta,
    dto_evidence,
    init_dto_episode,
    macro_proxy_score,
)
from rs_cx23.common import apply_class_edit, class_key, class_parts
from rs_cx23 import cx23_c_haa as haa_mod
from rs_cx25.common import build_positive_negative_support, calibrate_margin, soft_downgrade_ctx


@dataclass(frozen=True)
class CX26BMGIParams:
    occ_thr: float
    trans_thr: float
    dynamic_thr: float
    support_slack: float
    budget_review: int
    budget_intervene: int
    margin_scale: float
    max_macros: int


def param_grid() -> list[CX26BMGIParams]:
    return [
        CX26BMGIParams(0.40, 0.40, 0.50, 0.22, 24, 12, 1.00, 3),
        CX26BMGIParams(0.35, 0.35, 0.45, 0.20, 20, 10, 0.80, 3),
        CX26BMGIParams(0.30, 0.30, 0.40, 0.18, 16, 8, 0.60, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-MGI', 'disable_mgi': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX26BMGIParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx25_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    dto_rows = compile_dto_contract_rows(calib_train_assets, stack, horizon_steps=int(stack.cx24_stack.haa_teacher.params.commit_steps + stack.cx24_stack.haa_teacher.params.recover_steps), stride=1)
    compiler = build_dto_compiler(dto_rows, min_hits=4)
    pos_support, neg_support = build_positive_negative_support(dto_rows, min_hits=4)
    margin_cfg = calibrate_margin(dto_rows, pos_support, neg_support, slack=float(params.support_slack))
    meta = {'params': params.__dict__, 'dto_contract': dto_contract_meta(), 'margin_cfg': margin_cfg}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'mgi_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'stack': stack, 'compiler': compiler, 'pos_support': pos_support, 'neg_support': neg_support, 'margin_cfg': margin_cfg, 'best_val_loss': float('nan')}


class MGIPolicy(DTOObservabilityMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX26BMGIParams, memory: dict[str, Any], disable_mgi: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_mgi = bool(disable_mgi)
        self.stack = memory['stack']
        self.compiler = memory['compiler']
        self.pos_support = dict(memory['pos_support'])
        self.neg_support = dict(memory['neg_support'])
        self.margin_cfg = dict(memory['margin_cfg'])
        self.inner = make_haa_policy(self.stack.cx24_stack.haa_teacher, case, bundle, self.field)
        self._dto_diag_init()

    def start_search(self, planner, start, goal, h_pair, search_state):
        init_dto_episode(search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        evidence = dto_evidence(self.compiler, ctx, search_state, self.case, self.bundle, support_slack=float(self.params.support_slack))
        ctx['dto_evidence'] = evidence
        self._dto_diag_record(record, search_state, ctx, evidence)
        return ctx

    def _trigger(self, evidence: dict[str, Any], search_state: dict[str, Any]) -> bool:
        gate1 = bool(
            float(evidence.get('occupancy_hotspot_score', 0.0)) >= float(self.params.occ_thr)
            or float(evidence.get('transition_hotspot_score', 0.0)) >= float(self.params.trans_thr)
            or float(evidence.get('false_commit_ledger_hit', 0.0)) >= 1.0
        )
        dynamic_score = float(
            0.35 * float(evidence.get('churn_score', 0.0))
            + 0.25 * float(evidence.get('commit_recover_loop_score', 0.0))
            + 0.25 * float(evidence.get('local_proxy_disagreement', 0.0))
            + 0.15 * float(evidence.get('sibling_inconsistency', 0.0))
        )
        gate2 = bool(dynamic_score >= float(self.params.dynamic_thr))
        gate3 = bool(int(search_state.get('dto_review_count', 0)) < int(self.params.budget_review))
        return bool(gate1 and gate2 and gate3)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_mgi or not isinstance(node_ctx, dict) or str(search_state.get('haa_state', 'observe')) != 'commit':
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        evidence = dict(node_ctx.get('dto_evidence', {}))
        if not self._trigger(evidence, search_state):
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        search_state['dto_review_count'] = int(search_state.get('dto_review_count', 0)) + 1
        current_key = str(class_key(node_ctx))
        commit_score, best_sib, sibling_score = macro_proxy_score(self.case, planner, record, h_pair, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, current_key, max_macros=int(self.params.max_macros))
        baseline_score = max((float(record.g + record.guided) - (record.g + float(c.guided)) for c in candidates if getattr(c, 'source', 'primitive') == 'primitive'), default=float('-inf'))
        feat = np.asarray(evidence.get('trace_feature', []), dtype=np.float32)
        # use scalar risk/intensity only
        z_risk = float(
            0.30 * float(evidence.get('occupancy_hotspot_score', 0.0))
            + 0.20 * float(evidence.get('transition_hotspot_score', 0.0))
            + 0.20 * float(evidence.get('local_proxy_disagreement', 0.0))
            + 0.15 * float(evidence.get('commit_recover_loop_score', 0.0))
            + 0.15 * float(evidence.get('sibling_inconsistency', 0.0))
        )
        margin_fail = max(baseline_score, sibling_score) - commit_score
        z_margin = float(np.clip(margin_fail / max(float(self.params.margin_scale), 1e-6), 0.0, 1.0))
        z = float(np.clip(0.5 * z_risk + 0.5 * z_margin, 0.0, 1.0))
        node_ctx['mgi_z'] = z
        if z >= 0.75:
            edited = apply_class_edit(node_ctx, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
            node_ctx.clear(); node_ctx.update(edited)
            search_state['haa_state'] = 'recover'
            search_state['dto_intervene_count'] = int(search_state.get('dto_intervene_count', 0)) + 1
        elif z >= 0.50 and best_sib != 'none':
            mode, _ = class_parts(current_key)
            edited = apply_class_edit(node_ctx, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, f'{mode}|{best_sib}', max_macros=int(self.params.max_macros))
            node_ctx.clear(); node_ctx.update(edited)
            search_state['haa_support_count'] = max(int(self.stack.cx24_stack.haa_teacher.params.commit_steps * (1.0 - z)), 1)
            search_state['dto_intervene_count'] = int(search_state.get('dto_intervene_count', 0)) + 1
        elif z >= 0.25:
            edited = soft_downgrade_ctx(node_ctx, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, max_macros=int(self.params.max_macros), mode='mgi_soft')
            node_ctx.clear(); node_ctx.update(edited)
            search_state['haa_support_count'] = max(int(self.stack.cx24_stack.haa_teacher.params.commit_steps * (1.0 - z)), 1)
            search_state['dto_intervene_count'] = int(search_state.get('dto_intervene_count', 0)) + 1
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        complete_dto_episode(search_state, node_ctx if isinstance(node_ctx, dict) else None)


def make_policy(memory: dict[str, Any], params: CX26BMGIParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MGIPolicy(case, bundle, field, params, memory, disable_mgi=bool(ablation.get('disable_mgi', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX26BMGIParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].cx24_stack.haa_teacher.params, {'shadow_teacher': memory['stack'].cx24_stack.haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX26BMGIParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].cx24_stack.haa_teacher.params, {'shadow_teacher': memory['stack'].cx24_stack.haa_teacher.shadow_teacher}).astype(np.float32)
