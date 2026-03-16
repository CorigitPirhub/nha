from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx17.common import (
    FEATURE_NAMES,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_macro_subset,
    choose_motif_edges,
    compile_macro_library,
    compile_macro_support,
    compile_motif_automaton,
    compile_viability_table,
    feature_vector,
    macro_family,
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
class CX17CHPSParams:
    viability_gate: float
    oracle_gain_thr: float
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


def param_grid() -> list[CX17CHPSParams]:
    return [
        CX17CHPSParams(0.18, 0.03, 0.16, 2, 2, 0.08, 0.08, 0.10, 0.18, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2, 4),
        CX17CHPSParams(0.16, 0.025, 0.18, 2, 2, 0.10, 0.10, 0.12, 0.20, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2, 4),
        CX17CHPSParams(0.14, 0.02, 0.20, 3, 3, 0.12, 0.12, 0.14, 0.22, 0.20, 0.26, 0.36, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Substrate', 'disable_substrate': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX17CHPSParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.max_macros))
    macro_support = compile_macro_support(calib_train_assets, spec, macros, table, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    automaton, automaton_support = compile_motif_automaton(calib_train_assets, spec, table, horizon_steps=int(params.horizon_steps), min_gain=0.10)
    save_meta(
        out_dir / 'hps_meta.json',
        {
            'params': params.__dict__,
            'num_macros': int(len(macros)),
            'num_automaton_entries': int(len(automaton)),
            'macro_support': serializable_support(macro_support),
            'automaton_support': {','.join(map(str, k)): serializable_support(v) for k, v in automaton_support.items()},
        },
    )
    return {
        'viability_table': table,
        'macros': macros,
        'macro_support': macro_support,
        'automaton': automaton,
        'automaton_support': automaton_support,
        'best_val_loss': float('nan'),
    }


class HPSPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX17CHPSParams, memory: dict[str, Any], disable_substrate: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_substrate = bool(disable_substrate)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
        self.macro_support = dict(memory.get('macro_support', {})) if isinstance(memory, dict) else {}
        self.automaton = dict(memory.get('automaton', {})) if isinstance(memory, dict) else {}
        self.automaton_support = dict(memory.get('automaton_support', {})) if isinstance(memory, dict) else {}

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
        macros = [] if self.disable_substrate else choose_macro_subset(
            self.macros,
            self.macro_support,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_macros=int(self.params.max_macros),
        )
        edges = [] if self.disable_substrate else choose_motif_edges(
            self.automaton.get(entry_key, []),
            self.automaton_support.get(entry_key, {}),
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_edges=int(self.params.max_edges),
        )
        mode = 'local'
        if float(oracle_gain) >= float(self.params.oracle_gain_thr) and macros:
            mode = 'macro'
        elif edges:
            mode = 'motif'
        elif float(margin) <= float(self.params.viability_gate):
            mode = 'border'
        target_vec = None
        if mode == 'border':
            border = self.encoder.best_border_key(stats.key, 2)
            if border is not None:
                cx, cy, _ = self.encoder.bucket_center(stats.key)
                tx, ty, _ = self.encoder.bucket_center(border)
                target_vec = (float(tx - cx), float(ty - cy))
        return {'stats': stats, 'margin': float(margin), 'oracle_gain': float(oracle_gain), 'macros': macros, 'edges': edges, 'mode': str(mode), 'target_vec': target_vec}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_substrate or not isinstance(node_ctx, dict):
            return []
        mode = str(node_ctx.get('mode', 'local'))
        if mode == 'macro':
            return macro_successor_candidates(self.case, planner, record, h_pair, list(node_ctx.get('macros', [])), max_macros=int(self.params.max_macros))
        if mode == 'motif':
            macros = []
            for idx, edge in enumerate(node_ctx.get('edges', []), start=1):
                macros.append(MacroPrimitive(name=f'motif_{idx}', primitive_indices=tuple(edge.sequence), family=str(edge.family), avg_gain=float(edge.avg_gain), hits=int(edge.hits)))
            return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))
        return []

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_substrate or not isinstance(node_ctx, dict):
            return None
        mode = str(node_ctx.get('mode', 'local'))
        current_margin = float(node_ctx.get('margin', 0.0))
        reverse_need = float(reverse_need_score(node_ctx['stats'], self.spec))
        family_set = {str(getattr(edge, 'family', '')) for edge in node_ctx.get('edges', [])}
        macro_set = {str(getattr(m, 'name', '')) for m in node_ctx.get('macros', [])}
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.review_gain) * float(cand_margin - current_margin)
            if mode == 'macro' and getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            if mode == 'motif' and getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.motif_bonus)
            if getattr(cand, 'family', None) in family_set:
                delta -= 0.06
            if mode == 'border' and node_ctx.get('target_vec') is not None:
                tx, ty = map(float, node_ctx['target_vec'])
                mdx = float(cand.next_state[0] - float(record.x))
                mdy = float(cand.next_state[1] - float(record.y))
                mnorm = float(math.hypot(mdx, mdy))
                tnorm = float(math.hypot(tx, ty))
                align = 0.0 if mnorm <= 1e-6 or tnorm <= 1e-6 else float((mdx * tx + mdy * ty) / (mnorm * tnorm))
                delta -= float(self.params.border_bonus) * align
            if float(reverse_need) > 0.08 and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX17CHPSParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return HPSPolicy(case, bundle, params, memory, disable_substrate=bool(ablation.get('disable_substrate', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX17CHPSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx17_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX17CHPSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
