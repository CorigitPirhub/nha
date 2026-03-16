from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx17.common import (
    MotifEdge,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_motif_edges,
    compile_motif_automaton,
    compile_viability_table,
    feature_vector,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    serializable_support,
)
from rs_cx16.common import MacroPrimitive


@dataclass(frozen=True)
class CX17BMAGParams:
    trigger_margin: float
    oracle_gain_thr: float
    support_slack: float
    max_edges: int
    macro_bonus: float
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


def param_grid() -> list[CX17BMAGParams]:
    return [
        CX17BMAGParams(0.18, 0.03, 0.15, 2, 0.10, 0.08, 0.22, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2, 5),
        CX17BMAGParams(0.16, 0.025, 0.18, 2, 0.12, 0.10, 0.24, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2, 5),
        CX17BMAGParams(0.14, 0.02, 0.20, 3, 0.14, 0.12, 0.26, 0.20, 0.26, 0.36, 0.24, 0.10, 0.04, 0.08, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Automaton', 'disable_automaton': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX17BMAGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    automaton, support = compile_motif_automaton(calib_train_assets, spec, table, horizon_steps=int(params.horizon_steps), min_gain=0.10)
    save_meta(
        out_dir / 'mag_meta.json',
        {
            'params': params.__dict__,
            'num_entries': int(len(automaton)),
            'entry_sizes': {','.join(map(str, k)): len(v) for k, v in automaton.items()},
            'support': {','.join(map(str, k)): serializable_support(v) for k, v in support.items()},
        },
    )
    return {'viability_table': table, 'automaton': automaton, 'support': support, 'best_val_loss': float('nan')}


class MAGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX17BMAGParams, memory: dict[str, Any], disable_automaton: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_automaton = bool(disable_automaton)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.automaton = dict(memory.get('automaton', {})) if isinstance(memory, dict) else {}
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
        entry_key = margin_key(stats)
        oracle = query_viability_table(self.table, entry_key)
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        margin = self._margin(stats)
        feat = feature_vector(stats, margin, oracle_gain, self.spec)
        edges = [] if self.disable_automaton else choose_motif_edges(
            self.automaton.get(entry_key, []),
            self.support.get(entry_key, {}),
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_edges=int(self.params.max_edges),
        )
        active = bool(edges and (float(margin) <= float(self.params.trigger_margin) or float(oracle_gain) >= float(self.params.oracle_gain_thr)))
        return {'stats': stats, 'margin': float(margin), 'oracle_gain': float(oracle_gain), 'edges': edges, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_automaton or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        macros = []
        for idx, edge in enumerate(node_ctx.get('edges', []), start=1):
            macros.append(
                MacroPrimitive(
                    name=f'motif_{idx}',
                    primitive_indices=tuple(edge.sequence),
                    family=str(edge.family),
                    avg_gain=float(edge.avg_gain),
                    hits=int(edge.hits),
                )
            )
        return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_automaton or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_margin = float(node_ctx.get('margin', 0.0))
        reverse_need = float(reverse_need_score(node_ctx['stats'], self.spec))
        family_set = {str(edge.family) for edge in node_ctx.get('edges', [])}
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.improve_gain) * float(cand_margin - current_margin)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            if getattr(cand, 'family', None) in family_set:
                delta -= float(self.params.family_bonus)
            if float(reverse_need) > 0.08 and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX17BMAGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MAGPolicy(case, bundle, params, memory, disable_automaton=bool(ablation.get('disable_automaton', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX17BMAGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx17_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX17BMAGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
