from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx16.common import MacroPrimitive
from rs_cx18.common import (
    RecoverabilityEncoder,
    RecoverabilitySpec,
    ViabilityStateConfig,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_state_motif_edges,
    classify_viability_state,
    compile_motif_compiler_graph,
    compile_viability_table,
    feature_vector,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    serializable_support_state,
)


@dataclass(frozen=True)
class CX18BMCGParams:
    safe_margin: float
    boundary_margin: float
    reverse_need_thr: float
    oracle_gain_thr: float
    trap_high_thr: float
    corridor_low_thr: float
    support_slack: float
    max_edges: int
    motif_bonus: float
    family_bonus: float
    improve_gain: float
    clearance_w: float
    corridor_w: float
    trap_w: float
    reverse_w: float
    lateral_w: float
    forward_w: float
    heading_w: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX18BMCGParams]:
    return [
        CX18BMCGParams(0.22, 0.12, 0.07, 0.02, 0.55, 0.35, 0.16, 2, 0.10, 0.08, 0.22, 0.20, 0.26, 0.34, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
        CX18BMCGParams(0.20, 0.10, 0.06, 0.02, 0.52, 0.38, 0.18, 2, 0.12, 0.10, 0.24, 0.20, 0.26, 0.36, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
        CX18BMCGParams(0.18, 0.08, 0.05, 0.015, 0.50, 0.40, 0.20, 3, 0.14, 0.12, 0.26, 0.18, 0.28, 0.38, 0.26, 0.10, 0.04, 0.08, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Compiler-Graph', 'disable_motif_graph': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX18BMCGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    state_cfg = ViabilityStateConfig(
        safe_margin=float(params.safe_margin),
        boundary_margin=float(params.boundary_margin),
        reverse_need_thr=float(params.reverse_need_thr),
        oracle_gain_thr=float(params.oracle_gain_thr),
        trap_high_thr=float(params.trap_high_thr),
        corridor_low_thr=float(params.corridor_low_thr),
    )
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    graph, support = compile_motif_compiler_graph(calib_train_assets, spec, state_cfg, table, horizon_steps=int(params.horizon_steps), min_gain=0.10)
    save_meta(
        out_dir / 'mcg_meta.json',
        {
            'params': params.__dict__,
            'state_cfg': state_cfg.__dict__,
            'num_states': {state: len(edges) for state, edges in graph.items()},
            'support': serializable_support_state(support),
        },
    )
    return {'viability_table': table, 'graph': graph, 'support': support, 'best_val_loss': float('nan')}


class MCGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX18BMCGParams, memory: dict[str, Any], disable_motif_graph: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_motif_graph = bool(disable_motif_graph)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.state_cfg = ViabilityStateConfig(
            safe_margin=float(params.safe_margin),
            boundary_margin=float(params.boundary_margin),
            reverse_need_thr=float(params.reverse_need_thr),
            oracle_gain_thr=float(params.oracle_gain_thr),
            trap_high_thr=float(params.trap_high_thr),
            corridor_low_thr=float(params.corridor_low_thr),
        )
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.graph = dict(memory.get('graph', {})) if isinstance(memory, dict) else {}
        self.support = dict(memory.get('support', {})) if isinstance(memory, dict) else {}

    def _margin(self, stats) -> float:
        return recoverability_margin(
            stats,
            clearance_w=float(self.params.clearance_w),
            corridor_w=float(self.params.corridor_w),
            trap_w=float(self.params.trap_w),
            reverse_w=float(self.params.reverse_w),
            lateral_w=float(self.params.lateral_w),
            forward_w=float(self.params.forward_w),
            heading_w=float(self.params.heading_w),
            spec=self.spec,
        )

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        stats = self.encoder.features((float(record.x), float(record.y), float(record.yaw)))
        margin = self._margin(stats)
        oracle = query_viability_table(self.table, margin_key(stats))
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        state = classify_viability_state(stats, margin, oracle_gain, self.state_cfg, self.spec)
        feat = feature_vector(stats, margin, oracle_gain, self.spec)
        edges = [] if self.disable_motif_graph else choose_state_motif_edges(
            state,
            self.graph,
            self.support,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_edges=int(self.params.max_edges),
        )
        active = bool(edges and str(state) != 'safe_progress')
        return {'stats': stats, 'margin': float(margin), 'state': str(state), 'edges': edges, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_motif_graph or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        macros = []
        for idx, edge in enumerate(node_ctx.get('edges', []), start=1):
            macros.append(MacroPrimitive(name=f'mcg_{idx}', primitive_indices=tuple(edge.sequence), family=str(edge.family), avg_gain=float(edge.avg_gain), hits=int(edge.hits)))
        return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_motif_graph or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        state = str(node_ctx.get('state', 'safe_progress'))
        current_margin = float(node_ctx.get('margin', 0.0))
        reverse_need = float(reverse_need_score(node_ctx['stats'], self.spec))
        family_set = {str(edge.family) for edge in node_ctx.get('edges', [])}
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.improve_gain) * float(cand_margin - current_margin)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.motif_bonus)
            if getattr(cand, 'family', None) in family_set:
                delta -= float(self.params.family_bonus)
            if state == 'reverse_required' and int(cand.direction) < 0:
                delta -= 0.04
            if float(reverse_need) > float(self.params.reverse_need_thr) and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX18BMCGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MCGPolicy(case, bundle, params, memory, disable_motif_graph=bool(ablation.get('disable_motif_graph', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX18BMCGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx18_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX18BMCGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
