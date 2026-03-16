from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx19.common import (
    RecoverabilityEncoder,
    RecoverabilitySpec,
    ViabilityStateConfig,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_state_macros,
    classify_viability_state,
    compile_macro_library,
    compile_state_macro_support,
    compile_viability_table,
    feature_vector,
    macro_family,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    serializable_support_state,
    state_family_bonus,
)


@dataclass(frozen=True)
class CX19AVMGParams:
    safe_margin: float
    boundary_margin: float
    reverse_need_thr: float
    oracle_gain_thr: float
    trap_high_thr: float
    corridor_low_thr: float
    support_slack: float
    max_macros: int
    macro_bonus: float
    grammar_bonus: float
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


def param_grid() -> list[CX19AVMGParams]:
    return [
        CX19AVMGParams(0.24, 0.14, 0.07, 0.02, 0.56, 0.34, 0.18, 2, 0.12, 0.10, 0.26, 0.20, 0.26, 0.36, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
        CX19AVMGParams(0.22, 0.12, 0.06, 0.02, 0.54, 0.36, 0.20, 3, 0.14, 0.12, 0.28, 0.18, 0.28, 0.38, 0.26, 0.10, 0.04, 0.08, 2, 2, 5),
        CX19AVMGParams(0.20, 0.10, 0.05, 0.015, 0.52, 0.38, 0.22, 3, 0.16, 0.14, 0.30, 0.18, 0.28, 0.40, 0.26, 0.10, 0.04, 0.08, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Grammar', 'disable_grammar': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX19AVMGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
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
    support, counts = compile_state_macro_support(calib_train_assets, spec, state_cfg, macros, table, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    save_meta(out_dir / 'vmg_meta.json', {'params': params.__dict__, 'state_cfg': state_cfg.__dict__, 'support': serializable_support_state(support), 'counts': counts})
    return {'viability_table': table, 'macros': macros, 'support': support, 'counts': counts, 'best_val_loss': float('nan')}


class VMGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX19AVMGParams, memory: dict[str, Any], disable_grammar: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_grammar = bool(disable_grammar)
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
        self.support = dict(memory.get('support', {})) if isinstance(memory, dict) else {}
        self.counts = dict(memory.get('counts', {})) if isinstance(memory, dict) else {}

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
        macros = [] if self.disable_grammar else choose_state_macros(
            state,
            self.macros,
            self.support,
            self.counts,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_macros=int(self.params.max_macros),
        )
        active = bool(str(state) != 'safe_progress' and macros)
        return {'stats': stats, 'margin': float(margin), 'oracle_gain': float(oracle_gain), 'state': str(state), 'macros': macros, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_grammar or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, list(node_ctx.get('macros', [])), max_macros=int(self.params.max_macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_grammar or not isinstance(node_ctx, dict):
            return None
        state = str(node_ctx.get('state', 'safe_progress'))
        current_margin = float(node_ctx.get('margin', 0.0))
        reverse_need = float(reverse_need_score(node_ctx['stats'], self.spec))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.improve_gain) * float(cand_margin - current_margin)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            delta -= float(self.params.grammar_bonus) * float(state_family_bonus(state, macro_family(cand), int(cand.direction)))
            if float(reverse_need) > float(self.params.reverse_need_thr) and int(cand.direction) < 0:
                delta -= 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX19AVMGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return VMGPolicy(case, bundle, params, memory, disable_grammar=bool(ablation.get('disable_grammar', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX19AVMGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx19_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX19AVMGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
