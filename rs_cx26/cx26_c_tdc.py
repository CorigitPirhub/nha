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
)
from rs_cx23 import cx23_c_haa as haa_mod
from rs_cx11.common import fit_support_band, support_match
from rs_cx25.common import soft_downgrade_ctx


@dataclass(frozen=True)
class CX26CTDCParams:
    min_hits: int
    support_slack: float
    tail_thr: float
    max_macros: int


def param_grid() -> list[CX26CTDCParams]:
    return [
        CX26CTDCParams(3, 0.22, 0.55, 3),
        CX26CTDCParams(4, 0.20, 0.50, 3),
        CX26CTDCParams(5, 0.18, 0.45, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-TDC', 'disable_tdc': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX26CTDCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx25_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    dto_rows = compile_dto_contract_rows(calib_train_assets, stack, horizon_steps=int(stack.cx24_stack.haa_teacher.params.commit_steps + stack.cx24_stack.haa_teacher.params.recover_steps), stride=1)
    compiler = build_dto_compiler(dto_rows, min_hits=4)
    tail_feats = []
    tail_gains = []
    for row in dto_rows:
        if str(row['scenario']) != 'parasol_misc' or float(row['future_gain']) > 0.0 or str(row['auto_state']) != 'commit':
            continue
        feat = np.asarray(row['trace_feature'], dtype=np.float32)
        # focus on structural inconsistency slice, not rarity
        structural = np.asarray([
            float(feat[-5]),  # support_count normalized-ish
            float(feat[-4]),  # recover_left
            float(feat[-2]),  # macro_count
            float(feat[6]),   # oracle_gain
            float(feat[7]),   # max_conf
            float(feat[8]),   # allowed_count
        ], dtype=np.float32)
        tail_feats.append(structural)
        tail_gains.append(float(row['future_gain']))
    tail_band = fit_support_band(tail_feats, tail_gains, low_q=0.05, high_q=0.95, sim_q=0.15) if len(tail_feats) >= int(params.min_hits) else None
    meta = {'params': params.__dict__, 'dto_contract': dto_contract_meta(), 'has_tail_band': bool(tail_band is not None)}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'tdc_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'stack': stack, 'compiler': compiler, 'tail_band': tail_band, 'best_val_loss': float('nan')}


class TDCPolicy(DTOObservabilityMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX26CTDCParams, memory: dict[str, Any], disable_tdc: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_tdc = bool(disable_tdc)
        self.stack = memory['stack']
        self.compiler = memory['compiler']
        self.tail_band = memory.get('tail_band')
        self.inner = make_haa_policy(self.stack.cx24_stack.haa_teacher, case, bundle, self.field)
        self._dto_diag_init()

    def start_search(self, planner, start, goal, h_pair, search_state):
        init_dto_episode(search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        evidence = dto_evidence(self.compiler, ctx, search_state, self.case, self.bundle)
        if not self.disable_tdc and self.tail_band is not None and str(search_state.get('haa_state', 'observe')) == 'commit':
            structural = np.asarray([
                float(search_state.get('haa_support_count', 0)),
                float(search_state.get('haa_recover_left', 0)),
                float(len(list(ctx.get('macros', [])))),
                float(ctx.get('oracle_gain', 0.0)),
                float(evidence.get('local_proxy_disagreement', 0.0)),
                float(evidence.get('sibling_inconsistency', 0.0)),
            ], dtype=np.float32)
            matched, sim = support_match(self.tail_band, structural, float(ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
            evidence['tail_structural_match'] = float(sim if matched else 0.0)
            # only affect tail-risk; avoid head families by requiring low hotspot and no ledger hit
            if matched and float(sim) >= float(self.params.tail_thr) and float(evidence.get('false_commit_ledger_hit', 0.0)) < 1.0 and float(evidence.get('occupancy_hotspot_score', 0.0)) < 0.4:
                ctx = soft_downgrade_ctx(ctx, self.stack.cx24_stack.haa_teacher.shadow_teacher.lag_teacher, max_macros=int(self.params.max_macros), mode='tail_defined')
                search_state['haa_support_count'] = max(int(search_state.get('haa_support_count', 0)) - 1, 0)
        ctx['dto_evidence'] = evidence
        self._dto_diag_record(record, search_state, ctx, evidence)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        complete_dto_episode(search_state, node_ctx if isinstance(node_ctx, dict) else None)


def make_policy(memory: dict[str, Any], params: CX26CTDCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return TDCPolicy(case, bundle, field, params, memory, disable_tdc=bool(ablation.get('disable_tdc', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX26CTDCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].cx24_stack.haa_teacher.params, {'shadow_teacher': memory['stack'].cx24_stack.haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX26CTDCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].cx24_stack.haa_teacher.params, {'shadow_teacher': memory['stack'].cx24_stack.haa_teacher.shadow_teacher}).astype(np.float32)
