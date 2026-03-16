from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx17.common import (
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    choose_macro_subset,
    compile_macro_library,
    compile_macro_support,
    compile_viability_table,
    feature_vector,
    margin_key,
    macro_family,
    macro_successor_candidates,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    serializable_support,
)


@dataclass(frozen=True)
class CX17AVMLParams:
    viability_gate: float
    oracle_gain_thr: float
    reverse_need_thr: float
    support_slack: float
    max_macros: int
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


def param_grid() -> list[CX17AVMLParams]:
    return [
        CX17AVMLParams(0.18, 0.03, 0.08, 0.15, 2, 0.10, 0.08, 0.22, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2, 4),
        CX17AVMLParams(0.16, 0.025, 0.07, 0.18, 2, 0.12, 0.10, 0.24, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2, 4),
        CX17AVMLParams(0.14, 0.02, 0.06, 0.20, 3, 0.14, 0.12, 0.26, 0.20, 0.26, 0.36, 0.24, 0.10, 0.04, 0.08, 2, 2, 5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Macro-Activation', 'disable_macros': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX17AVMLParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.max_macros))
    support = compile_macro_support(calib_train_assets, spec, macros, table, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    save_meta(
        out_dir / 'vml_meta.json',
        {
            'params': params.__dict__,
            'viability_table_size': int(len(table)),
            'macros': [m.__dict__ for m in macros],
            'support': serializable_support(support),
        },
    )
    return {'viability_table': table, 'macros': macros, 'support': support, 'best_val_loss': float('nan')}


class VMLPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX17AVMLParams, memory: dict[str, Any], disable_macros: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_macros = bool(disable_macros)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
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
        feat = feature_vector(stats, margin, oracle_gain, self.spec)
        macros = [] if self.disable_macros else choose_macro_subset(
            self.macros,
            self.support,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
            max_macros=int(self.params.max_macros),
        )
        active = bool(
            macros
            and (
                float(margin) <= float(self.params.viability_gate)
                or float(oracle_gain) >= float(self.params.oracle_gain_thr)
                or float(reverse_need_score(stats, self.spec)) >= float(self.params.reverse_need_thr)
            )
        )
        return {'stats': stats, 'margin': float(margin), 'oracle_gain': float(oracle_gain), 'macros': macros, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_macros or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, list(node_ctx.get('macros', [])), max_macros=int(self.params.max_macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_margin = float(node_ctx.get('margin', 0.0))
        macro_names = {str(m.name) for m in node_ctx.get('macros', [])}
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.improve_gain) * float(cand_margin - current_margin)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            fam = macro_family(cand)
            if any('reverse' in str(m.family) for m in node_ctx.get('macros', [])) and ('reverse' in fam or fam.startswith('B-')):
                delta -= float(self.params.family_bonus)
            if any(str(getattr(cand, 'source', '')) == 'macro' and str(getattr(m, 'name', '')) in macro_names for m in node_ctx.get('macros', [])):
                delta -= 0.02
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX17AVMLParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return VMLPolicy(case, bundle, params, memory, disable_macros=bool(ablation.get('disable_macros', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX17AVMLParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx17_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX17AVMLParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
