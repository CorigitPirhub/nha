from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx16.common import MacroPrimitive
from rs_cx21.common import (
    CVFModeConfig,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_stable_nodes,
    compile_family_support,
    compile_macro_library,
    compile_mode_support,
    compile_stable_graph,
    compile_viability_table,
    consistency_score,
    consistent_mode,
    family_bucket_name,
    foundation_feature_vector,
    foundation_state,
    macro_family,
    macro_successor_candidates,
    margin_key,
    match_mode_support,
    parse_stable_graph_family,
    query_viability_table,
    save_meta,
    serializable_family_support,
    serializable_graph,
    stable_graph_family_tag,
)


@dataclass(frozen=True)
class CX21CSCGParams:
    support_slack: float
    allowed_bonus: float
    graph_bonus: float
    local_refine_bonus: float
    local_refine_penalty: float
    macro_bonus: float
    improve_gain: float
    max_macros: int
    max_graph_nodes: int
    min_graph_hits: int
    forward_viability_thr: float
    reverse_required_thr: float
    trap_high_thr: float
    escape_affinity_low_thr: float
    hopeless_viability_thr: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX21CSCGParams]:
    return [
        CX21CSCGParams(0.18, 0.08, 0.10, 0.10, 0.12, 0.08, 0.14, 3, 2, 4, 0.34, 0.08, 0.56, -0.02, 0.10, 2, 2, 5),
        CX21CSCGParams(0.20, 0.10, 0.12, 0.12, 0.14, 0.10, 0.16, 3, 3, 4, 0.32, 0.07, 0.54, 0.00, 0.08, 2, 2, 5),
        CX21CSCGParams(0.22, 0.12, 0.14, 0.14, 0.16, 0.12, 0.18, 4, 3, 3, 0.30, 0.06, 0.50, 0.02, 0.06, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Stable-Graph', 'disable_graph': True},
        {'name': 'No-Support-Filter', 'disable_support_filter': True},
        {'name': 'No-Local-Refinement', 'disable_local_refinement': True},
    ]


def _mode_cfg(params: CX21CSCGParams) -> CVFModeConfig:
    return CVFModeConfig(
        forward_viability_thr=float(params.forward_viability_thr),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_high_thr=float(params.trap_high_thr),
        escape_affinity_low_thr=float(params.escape_affinity_low_thr),
        hopeless_viability_thr=float(params.hopeless_viability_thr),
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX21CSCGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    mode_cfg = _mode_cfg(params)
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    mode_support = compile_mode_support(calib_train_assets, spec, mode_cfg, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=max(int(params.max_macros) * 2, 4))
    family_support = compile_family_support(calib_train_assets, spec, mode_cfg, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    graph, graph_support = compile_stable_graph(
        calib_train_assets,
        spec,
        mode_cfg,
        horizon_steps=int(params.horizon_steps),
        min_gain=0.10,
        min_hits=int(params.min_graph_hits),
        max_nodes_per_mode=max(int(params.max_graph_nodes) * 2, 2),
    )
    save_meta(
        out_dir / 'scg_meta.json',
        {
            'params': params.__dict__,
            'mode_cfg': mode_cfg.__dict__,
            'family_support': serializable_family_support(family_support),
            'graph': serializable_graph(graph),
            'macros': [m.__dict__ for m in macros],
        },
    )
    return {
        'viability_table': table,
        'mode_support': mode_support,
        'family_support': family_support,
        'macros': macros,
        'graph': graph,
        'graph_support': graph_support,
        'best_val_loss': float('nan'),
    }


class SCGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX21CSCGParams, memory: dict[str, Any], disable_graph: bool = False, disable_support_filter: bool = False, disable_local_refinement: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_graph = bool(disable_graph)
        self.disable_support_filter = bool(disable_support_filter)
        self.disable_local_refinement = bool(disable_local_refinement)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.mode_cfg = _mode_cfg(params)
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.mode_support = dict(memory.get('mode_support', {})) if isinstance(memory, dict) else {}
        self.family_support = dict(memory.get('family_support', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
        self.graph = dict(memory.get('graph', {})) if isinstance(memory, dict) else {}
        self.graph_support = dict(memory.get('graph_support', {})) if isinstance(memory, dict) else {}

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        cur = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.encoder, state, self.spec)
        stats = self.encoder.features(state)
        oracle = query_viability_table(self.table, margin_key(stats))
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        feat = foundation_feature_vector(cur)
        support_mode, matched, _ = match_mode_support(self.mode_support, feat, gain_hint=max(float(oracle_gain), 0.0), slack=float(self.params.support_slack))
        mode = str(support_mode if bool(matched) else consistent_mode(cur, self.mode_cfg))
        graph_nodes = [] if self.disable_graph else choose_stable_nodes(
            mode,
            self.graph,
            self.graph_support,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_nodes=int(self.params.max_graph_nodes),
            use_support_filter=not bool(self.disable_support_filter),
        )
        graph_macros = [
            MacroPrimitive(
                name=f"scg_{idx}",
                primitive_indices=tuple(node.sequence),
                family=stable_graph_family_tag(node),
                avg_gain=float(node.avg_gain),
                hits=int(node.hits),
            )
            for idx, node in enumerate(graph_nodes, start=1)
        ]
        fallback_macros = list(self.macros[: int(max(self.params.max_macros, 0))])
        return {
            'foundation': cur,
            'mode': mode,
            'graph_nodes': graph_nodes,
            'graph_macros': graph_macros,
            'fallback_macros': fallback_macros,
        }

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return []
        macros = list(node_ctx.get('graph_macros', []))
        if not macros:
            macros = list(node_ctx.get('fallback_macros', []))
        if not macros:
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return None
        current = node_ctx.get('foundation')
        if current is None:
            return None
        current_cost = float(current.cost_to_go)
        current_viability = float(current.viability)
        ranked = []
        for cand in candidates:
            nf = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.encoder, cand.next_state, self.spec)
            cons = float(consistency_score(nf))
            delta = 0.0
            delta += float(self.params.improve_gain) * float(nf.cost_to_go - current_cost)
            delta -= 0.04 * float(nf.viability - current_viability)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            fam_bucket = family_bucket_name(macro_family(cand))
            recovered_mode = 'uncertain'
            lower_bound = 0.0
            hits = 0
            if str(macro_family(cand)).startswith('scg|'):
                fam_bucket, recovered_mode, lower_bound, hits = parse_stable_graph_family(macro_family(cand))
                delta -= float(self.params.graph_bonus)
                if not self.disable_local_refinement:
                    local_gain = float(current_cost - float(nf.cost_to_go))
                    if local_gain >= float(lower_bound):
                        delta -= float(self.params.local_refine_bonus) * float(cons)
                    else:
                        delta += float(self.params.local_refine_penalty)
                    cand_mode = consistent_mode(nf, self.mode_cfg)
                    if str(recovered_mode) != 'uncertain' and str(cand_mode) == str(recovered_mode):
                        delta -= 0.04
                    elif str(recovered_mode) != 'uncertain' and str(cand_mode) != str(recovered_mode):
                        delta += 0.04
                if int(hits) < int(self.params.min_graph_hits):
                    delta += 0.06
            if fam_bucket in {'reverse', 'reverse_setup'} and int(cand.direction) < 0:
                delta -= 0.02 * float(cons)
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX21CSCGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SCGPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_graph=bool(ablation.get('disable_graph', False)),
        disable_support_filter=bool(ablation.get('disable_support_filter', False)),
        disable_local_refinement=bool(ablation.get('disable_local_refinement', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX21CSCGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx21_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX21CSCGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
