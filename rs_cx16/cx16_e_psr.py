from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx16.common import (
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    compile_macro_library,
    compile_viability_table,
    increment_slot_counter,
    local_review_score,
    macro_family,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)


@dataclass(frozen=True)
class CX16EPSRParams:
    macro_gate: float
    border_radius: int
    top_macros: int
    macro_bonus: float
    border_align_bonus: float
    review_gain: float
    repeat_trigger: int
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


def param_grid() -> list[CX16EPSRParams]:
    return [
        CX16EPSRParams(0.18, 2, 2, 0.06, 0.10, 0.18, 1, 0.22, 0.24, 0.30, 0.20, 0.10, 0.06, 0.08, 2, 2, 4),
        CX16EPSRParams(0.16, 2, 3, 0.08, 0.12, 0.20, 1, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2, 4),
        CX16EPSRParams(0.14, 3, 3, 0.10, 0.14, 0.22, 2, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2, 5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Substrate', 'disable_substrate': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX16EPSRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.top_macros))
    save_meta(
        out_dir / 'psr_meta.json',
        {'params': params.__dict__, 'table': {','.join(map(str, k)): v for k, v in table.items()}, 'macros': [m.__dict__ for m in macros]},
    )
    return {'viability_table': table, 'macros': macros, 'best_val_loss': float('nan')}


class PSRPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX16EPSRParams, memory: dict[str, Any], disable_substrate: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_substrate = bool(disable_substrate)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
        self.seen_slot = '_cx16_e_seen'
        self.stall_slot = '_cx16_e_stall'

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
        seen = int(search_state.get(self.seen_slot, {}).get(stats.key, 0)) if isinstance(search_state.get(self.seen_slot, None), dict) else 0
        oracle = query_viability_table(self.table, margin_key(stats))
        mode = 'local'
        target_vec = None
        if not self.disable_substrate and (float(margin) <= float(self.params.macro_gate) or int(seen) >= int(self.params.repeat_trigger)):
            mode = 'macro'
            border = self.encoder.best_border_key(stats.key, int(self.params.border_radius))
            if border is not None:
                cx, cy, _ = self.encoder.bucket_center(stats.key)
                tx, ty, _ = self.encoder.bucket_center(border)
                target_vec = (float(tx - cx), float(ty - cy))
        return {'stats': stats, 'margin': float(margin), 'mode': str(mode), 'target_vec': target_vec, 'oracle': oracle}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_substrate or not isinstance(node_ctx, dict) or str(node_ctx.get('mode', 'local')) != 'macro':
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, self.macros, max_macros=int(self.params.top_macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_substrate or not isinstance(node_ctx, dict):
            return None
        current_stats = node_ctx['stats']
        current_margin = float(node_ctx['margin'])
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        mode = str(node_ctx.get('mode', 'local'))
        target_vec = node_ctx.get('target_vec', None)
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            family = macro_family(cand)
            score = local_review_score(stats, current_margin, candidate_margin=cand_margin, reverse_need=reverse_need, family=family)
            if mode == 'macro' and getattr(cand, 'source', 'primitive') == 'macro':
                score += float(self.params.macro_bonus)
            if mode == 'macro' and target_vec is not None:
                tx, ty = map(float, target_vec)
                mdx = float(cand.next_state[0] - float(record.x))
                mdy = float(cand.next_state[1] - float(record.y))
                mnorm = float(math.hypot(mdx, mdy))
                tnorm = float(math.hypot(tx, ty))
                align = 0.0 if mnorm <= 1e-6 or tnorm <= 1e-6 else float((mdx * tx + mdy * ty) / (mnorm * tnorm))
                score += float(self.params.border_align_bonus) * align
            delta = -float(self.params.review_gain) * score
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return
        stats = node_ctx.get('stats', None)
        if stats is None:
            return
        increment_slot_counter(search_state, self.seen_slot, stats.key)
        event_hit = bool(int(accepted_local) == 0 or str(node_ctx.get('mode', 'local')) == 'macro')
        update_global_stall(search_state, self.stall_slot, bool(event_hit))


def make_policy(memory: dict[str, Any], params: CX16EPSRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return PSRPolicy(case, bundle, params, memory, disable_substrate=bool(ablation.get('disable_substrate', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX16EPSRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx16_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX16EPSRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
