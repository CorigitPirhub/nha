from __future__ import annotations

import math
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
    choose_state_macros,
    choose_state_motif_edges,
    classify_viability_state,
    compile_macro_library,
    compile_motif_compiler_graph,
    compile_state_macro_support,
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
class CX18CGPSParams:
    safe_margin: float
    boundary_margin: float
    reverse_need_thr: float
    oracle_gain_thr: float
    trap_high_thr: float
    corridor_low_thr: float
    support_slack: float
    max_macros: int
    max_edges: int
    macro_bonus: float
    motif_bonus: float
    border_bonus: float
    review_gain: float
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


def param_grid() -> list[CX18CGPSParams]:
    return [
        CX18CGPSParams(0.22, 0.12, 0.07, 0.02, 0.55, 0.35, 0.16, 2, 2, 0.10, 0.10, 0.12, 0.20, 0.20, 0.26, 0.34, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
        CX18CGPSParams(0.20, 0.10, 0.06, 0.02, 0.52, 0.38, 0.18, 3, 2, 0.12, 0.12, 0.14, 0.22, 0.18, 0.28, 0.36, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
        CX18CGPSParams(0.18, 0.08, 0.05, 0.015, 0.50, 0.40, 0.20, 3, 3, 0.14, 0.14, 0.16, 0.24, 0.18, 0.28, 0.38, 0.26, 0.10, 0.04, 0.08, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Graph-Substrate', 'disable_substrate': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX18CGPSParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
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
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.max_macros))
    macro_support, macro_counts = compile_state_macro_support(calib_train_assets, spec, state_cfg, macros, table, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    graph, graph_support = compile_motif_compiler_graph(calib_train_assets, spec, state_cfg, table, horizon_steps=int(params.horizon_steps), min_gain=0.10)
    save_meta(
        out_dir / 'gps_meta.json',
        {
            'params': params.__dict__,
            'state_cfg': state_cfg.__dict__,
            'num_macros': int(len(macros)),
            'graph_sizes': {state: len(edges) for state, edges in graph.items()},
            'macro_support': serializable_support_state(macro_support),
            'graph_support': serializable_support_state(graph_support),
        },
    )
    return {
        'viability_table': table,
        'macros': macros,
        'macro_support': macro_support,
        'macro_counts': macro_counts,
        'graph': graph,
        'graph_support': graph_support,
        'best_val_loss': float('nan'),
    }


class GPSPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX18CGPSParams, memory: dict[str, Any], disable_substrate: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_substrate = bool(disable_substrate)
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
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
        self.macro_support = dict(memory.get('macro_support', {})) if isinstance(memory, dict) else {}
        self.macro_counts = dict(memory.get('macro_counts', {})) if isinstance(memory, dict) else {}
        self.graph = dict(memory.get('graph', {})) if isinstance(memory, dict) else {}
        self.graph_support = dict(memory.get('graph_support', {})) if isinstance(memory, dict) else {}

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
        macros = [] if self.disable_substrate else choose_state_macros(
            state,
            self.macros,
            self.macro_support,
            self.macro_counts,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_macros=int(self.params.max_macros),
        )
        edges = [] if self.disable_substrate else choose_state_motif_edges(
            state,
            self.graph,
            self.graph_support,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_edges=int(self.params.max_edges),
        )
        mode = 'local'
        if str(state) == 'reverse_required' and macros:
            mode = 'macro'
        elif str(state) == 'near_trap' and edges:
            mode = 'motif'
        elif str(state) == 'recoverable_boundary' and macros:
            mode = 'macro'
        elif str(state) == 'recoverable_boundary' and edges:
            mode = 'motif'
        elif float(margin) <= float(self.params.boundary_margin):
            mode = 'border'
        target_vec = None
        if mode == 'border':
            border = self.encoder.best_border_key(stats.key, 2)
            if border is not None:
                cx, cy, _ = self.encoder.bucket_center(stats.key)
                tx, ty, _ = self.encoder.bucket_center(border)
                target_vec = (float(tx - cx), float(ty - cy))
        return {'stats': stats, 'margin': float(margin), 'state': str(state), 'oracle_gain': float(oracle_gain), 'macros': macros, 'edges': edges, 'mode': str(mode), 'target_vec': target_vec}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_substrate or not isinstance(node_ctx, dict):
            return []
        mode = str(node_ctx.get('mode', 'local'))
        if mode == 'macro':
            return macro_successor_candidates(self.case, planner, record, h_pair, list(node_ctx.get('macros', [])), max_macros=int(self.params.max_macros))
        if mode == 'motif':
            macros = []
            for idx, edge in enumerate(node_ctx.get('edges', []), start=1):
                macros.append(MacroPrimitive(name=f'mcg_{idx}', primitive_indices=tuple(edge.sequence), family=str(edge.family), avg_gain=float(edge.avg_gain), hits=int(edge.hits)))
            return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))
        return []

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_substrate or not isinstance(node_ctx, dict):
            return None
        mode = str(node_ctx.get('mode', 'local'))
        state = str(node_ctx.get('state', 'safe_progress'))
        current_margin = float(node_ctx.get('margin', 0.0))
        reverse_need = float(reverse_need_score(node_ctx['stats'], self.spec))
        family_set = {str(edge.family) for edge in node_ctx.get('edges', [])}
        macro_names = {str(m.name) for m in node_ctx.get('macros', [])}
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.review_gain) * float(cand_margin - current_margin)
            if mode == 'macro' and getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            if mode == 'motif' and getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.motif_bonus)
            fam = str(getattr(cand, 'family', ''))
            if fam in family_set:
                delta -= 0.06
            if state == 'reverse_required' and int(cand.direction) < 0:
                delta -= 0.04
            if mode == 'border' and node_ctx.get('target_vec') is not None:
                tx, ty = map(float, node_ctx['target_vec'])
                mdx = float(cand.next_state[0] - float(record.x))
                mdy = float(cand.next_state[1] - float(record.y))
                mnorm = float(math.hypot(mdx, mdy))
                tnorm = float(math.hypot(tx, ty))
                align = 0.0 if mnorm <= 1e-6 or tnorm <= 1e-6 else float((mdx * tx + mdy * ty) / (mnorm * tnorm))
                delta -= float(self.params.border_bonus) * align
            if str(getattr(cand, 'source', '')) == 'macro' and any(str(getattr(m, 'name', '')) in macro_names for m in node_ctx.get('macros', [])):
                delta -= 0.02
            if float(reverse_need) > float(self.params.reverse_need_thr) and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX18CGPSParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return GPSPolicy(case, bundle, params, memory, disable_substrate=bool(ablation.get('disable_substrate', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX18CGPSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx18_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX18CGPSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
