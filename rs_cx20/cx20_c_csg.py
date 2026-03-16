from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx16.common import MacroPrimitive
from rs_cx20.common import (
    CompilerNode,
    GrammarStateConfig,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_graph_nodes,
    choose_head_macros,
    classify_grammar_state,
    compile_foundation_graph,
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
class CX20CCSGParams:
    safe_cost: float
    boundary_viability: float
    reverse_required_thr: float
    oracle_gain_thr: float
    trap_high_thr: float
    support_slack: float
    max_macros: int
    max_edges: int
    macro_bonus: float
    motif_bonus: float
    border_bonus: float
    grammar_bonus: float
    improve_gain: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX20CCSGParams]:
    return [
        CX20CCSGParams(12.0, 0.18, 0.08, 0.02, 0.55, 0.16, 2, 2, 0.10, 0.10, 0.12, 0.10, 0.20, 2, 2, 5),
        CX20CCSGParams(10.0, 0.16, 0.07, 0.02, 0.52, 0.18, 3, 2, 0.12, 0.12, 0.14, 0.12, 0.22, 2, 2, 5),
        CX20CCSGParams(8.0, 0.14, 0.06, 0.015, 0.50, 0.20, 3, 3, 0.14, 0.14, 0.16, 0.14, 0.24, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Compiled-Graph', 'disable_graph': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX20CCSGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
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
    graph, graph_support = compile_foundation_graph(calib_train_assets, spec, grammar_cfg, horizon_steps=int(params.horizon_steps), min_gain=0.10)
    save_meta(out_dir / 'csg_meta.json', {'params': params.__dict__, 'grammar_cfg': grammar_cfg.__dict__, 'support': serializable_support_state(support), 'graph_support': serializable_support_state(graph_support)})
    return {'viability_table': table, 'macros': macros, 'support': support, 'counts': counts, 'graph': graph, 'graph_support': graph_support, 'best_val_loss': float('nan')}


class CSGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX20CCSGParams, memory: dict[str, Any], disable_graph: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_graph = bool(disable_graph)
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
        self.graph = dict(memory.get('graph', {})) if isinstance(memory, dict) else {}
        self.graph_support = dict(memory.get('graph_support', {})) if isinstance(memory, dict) else {}

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        f = foundation_state(self.case, self.case.get('_cx20_bundle', {}), self.field, self.encoder, (float(record.x), float(record.y), float(record.yaw)), self.spec)
        stats = self.encoder.features((float(record.x), float(record.y), float(record.yaw)))
        oracle = query_viability_table(self.table, margin_key(stats))
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        state = classify_grammar_state(f, self.grammar_cfg)
        feat = foundation_feature_vector(f)
        macros = [] if self.disable_graph else choose_head_macros(state, self.macros, self.support, self.counts, feat, gain_hint=max(float(oracle_gain), 0.0), slack=float(self.params.support_slack), max_macros=int(self.params.max_macros))
        nodes = [] if self.disable_graph else choose_graph_nodes(state, self.graph, self.graph_support, feat, gain_hint=max(float(oracle_gain), 0.0), slack=float(self.params.support_slack), max_edges=int(self.params.max_edges))
        mode = 'local'
        if str(state) == 'reverse_required' and macros:
            mode = 'macro'
        elif str(state) == 'escape_required' and nodes:
            mode = 'motif'
        elif str(state) == 'careful_boundary' and macros:
            mode = 'macro'
        elif str(state) == 'careful_boundary' and nodes:
            mode = 'motif'
        target_vec = None
        if mode == 'motif' and nodes:
            target_vec = (1.0, 0.0)
        return {'foundation': f, 'state': str(state), 'macros': macros, 'nodes': nodes, 'mode': str(mode), 'target_vec': target_vec}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_graph or not isinstance(node_ctx, dict):
            return []
        mode = str(node_ctx.get('mode', 'local'))
        if mode == 'macro':
            return macro_successor_candidates(self.case, planner, record, h_pair, list(node_ctx.get('macros', [])), max_macros=int(self.params.max_macros))
        if mode == 'motif':
            macros = []
            for idx, node in enumerate(node_ctx.get('nodes', []), start=1):
                macros.append(MacroPrimitive(name=f'csg_{idx}', primitive_indices=tuple(node.sequence), family=str(node.family), avg_gain=float(node.avg_gain), hits=int(node.hits)))
            return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))
        return []

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_graph or not isinstance(node_ctx, dict):
            return None
        state = str(node_ctx.get('state', 'direct_progress'))
        mode = str(node_ctx.get('mode', 'local'))
        f = node_ctx.get('foundation')
        current_cost = float(f.cost_to_go) if f is not None else 0.0
        target_vec = node_ctx.get('target_vec', None)
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            nf = foundation_state(self.case, self.case.get('_cx20_bundle', {}), self.field, self.encoder, cand.next_state, self.spec)
            fam = macro_family(cand)
            delta = float(self.params.improve_gain) * float(nf.cost_to_go - current_cost)
            if mode == 'macro' and getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            if mode == 'motif' and getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.motif_bonus)
            delta -= float(self.params.grammar_bonus) * float(grammar_family_bonus(state, fam, int(cand.direction)))
            if mode == 'motif' and target_vec is not None:
                tx, ty = map(float, target_vec)
                mdx = float(cand.next_state[0] - float(record.x))
                mdy = float(cand.next_state[1] - float(record.y))
                mnorm = float(math.hypot(mdx, mdy))
                tnorm = float(math.hypot(tx, ty))
                align = 0.0 if mnorm <= 1e-6 or tnorm <= 1e-6 else float((mdx * tx + mdy * ty) / (mnorm * tnorm))
                delta -= float(self.params.border_bonus) * align
            if float(reverse_need_score(stats, self.spec)) > float(self.params.reverse_required_thr) and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX20CCSGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CSGPolicy(case, bundle, field, params, memory, disable_graph=bool(ablation.get('disable_graph', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX20CCSGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx20_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX20CCSGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
