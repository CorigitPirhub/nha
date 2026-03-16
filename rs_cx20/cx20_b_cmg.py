from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx20.common import (
    GrammarStateConfig,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_head_macros,
    classify_grammar_state,
    compile_head_support,
    compile_macro_library,
    compile_viability_table,
    foundation_feature_vector,
    foundation_state,
    grammar_family_bonus,
    macro_family,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    reverse_need_score,
    save_meta,
    serializable_support_state,
)


@dataclass(frozen=True)
class CX20BCMGParams:
    safe_cost: float
    boundary_viability: float
    reverse_required_thr: float
    oracle_gain_thr: float
    trap_high_thr: float
    support_slack: float
    max_macros: int
    grammar_bonus: float
    macro_bonus: float
    improve_gain: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX20BCMGParams]:
    return [
        CX20BCMGParams(12.0, 0.18, 0.08, 0.02, 0.55, 0.16, 2, 0.10, 0.08, 0.24, 2, 2, 5),
        CX20BCMGParams(10.0, 0.16, 0.07, 0.02, 0.52, 0.18, 3, 0.12, 0.10, 0.26, 2, 2, 5),
        CX20BCMGParams(8.0, 0.14, 0.06, 0.015, 0.50, 0.20, 3, 0.14, 0.12, 0.28, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Grammar', 'disable_grammar': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX20BCMGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    grammar_cfg = GrammarStateConfig(
        safe_cost=float(params.safe_cost),
        boundary_viability=float(params.boundary_viability),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_escape_thr=0.0,
        trap_high_thr=float(params.trap_high_thr),
    )
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.max_macros))
    support, counts = compile_head_support(calib_train_assets, spec, grammar_cfg, macros, table, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    save_meta(out_dir / 'cmg_meta.json', {'params': params.__dict__, 'grammar_cfg': grammar_cfg.__dict__, 'support': serializable_support_state(support), 'counts': counts})
    return {'viability_table': table, 'macros': macros, 'support': support, 'counts': counts, 'best_val_loss': float('nan')}


class CMGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX20BCMGParams, memory: dict[str, Any], disable_grammar: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_grammar = bool(disable_grammar)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.grammar_cfg = GrammarStateConfig(
            safe_cost=float(params.safe_cost),
            boundary_viability=float(params.boundary_viability),
            reverse_required_thr=float(params.reverse_required_thr),
            trap_escape_thr=0.0,
            trap_high_thr=float(params.trap_high_thr),
        )
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
        self.support = dict(memory.get('support', {})) if isinstance(memory, dict) else {}
        self.counts = dict(memory.get('counts', {})) if isinstance(memory, dict) else {}

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        f = foundation_state(self.case, self.case.get('_cx20_bundle', {}), self.field, self.encoder, (float(record.x), float(record.y), float(record.yaw)), self.spec)
        stats = self.encoder.features((float(record.x), float(record.y), float(record.yaw)))
        oracle = query_viability_table(self.table, margin_key(stats))
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        state = classify_grammar_state(f, self.grammar_cfg)
        feat = foundation_feature_vector(f)
        macros = [] if self.disable_grammar else choose_head_macros(
            state,
            self.macros,
            self.support,
            self.counts,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_macros=int(self.params.max_macros),
        )
        active = bool(macros and str(state) != 'direct_progress')
        return {'foundation': f, 'state': str(state), 'macros': macros, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_grammar or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, list(node_ctx.get('macros', [])), max_macros=int(self.params.max_macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_grammar or not isinstance(node_ctx, dict):
            return None
        state = str(node_ctx.get('state', 'direct_progress'))
        cur = node_ctx.get('foundation')
        current_cost = float(cur.cost_to_go) if cur is not None else 0.0
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            f = foundation_state(self.case, self.case.get('_cx20_bundle', {}), self.field, self.encoder, cand.next_state, self.spec)
            delta = float(self.params.improve_gain) * float(f.cost_to_go - current_cost)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            delta -= float(self.params.grammar_bonus) * float(grammar_family_bonus(state, macro_family(cand), int(cand.direction)))
            if float(reverse_need_score(stats, self.spec)) > float(self.params.reverse_required_thr) and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX20BCMGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CMGPolicy(case, bundle, field, params, memory, disable_grammar=bool(ablation.get('disable_grammar', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX20BCMGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx20_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX20BCMGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
