from __future__ import annotations

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
    read_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)


@dataclass(frozen=True)
class CX16CBLRParams:
    trigger_margin: float
    progress_threshold: float
    accept_ratio_threshold: float
    repeat_trigger: int
    global_stall_trigger: int
    top_macros: int
    macro_bonus: float
    review_bonus: float
    family_bonus: float
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


def param_grid() -> list[CX16CBLRParams]:
    return [
        CX16CBLRParams(0.18, 0.010, 0.28, 1, 1, 2, 0.06, 0.18, 0.06, 0.22, 0.24, 0.30, 0.20, 0.10, 0.06, 0.08, 2, 2, 4),
        CX16CBLRParams(0.16, 0.012, 0.25, 1, 2, 2, 0.08, 0.20, 0.08, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2, 4),
        CX16CBLRParams(0.14, 0.015, 0.22, 2, 2, 3, 0.10, 0.22, 0.08, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2, 5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Review', 'disable_review': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX16CBLRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.top_macros))
    serializable_table = {','.join(map(str, key)): value for key, value in table.items()}
    serializable_macros = [macro.__dict__ for macro in macros]
    save_meta(out_dir / 'blr_meta.json', {'params': params.__dict__, 'table': serializable_table, 'macros': serializable_macros})
    return {'viability_table': table, 'macros': macros, 'best_val_loss': float('nan')}


class BLRPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX16CBLRParams, memory: dict[str, Any], disable_review: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_review = bool(disable_review)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []
        self.seen_slot = '_cx16_c_seen'
        self.stall_slot = '_cx16_c_stall'

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
        key = margin_key(stats)
        oracle = query_viability_table(self.table, key)
        progress = float(records[record.parent].anchor - record.anchor) if getattr(record, 'parent', None) in records else 0.0
        seen = read_slot_counter(search_state, self.seen_slot, stats.key)
        global_stall = int(search_state.get(self.stall_slot, 0))
        active = bool(
            (not self.disable_review)
            and (
                float(margin) <= float(self.params.trigger_margin)
                or float(progress) <= float(self.params.progress_threshold)
                or int(seen) >= int(self.params.repeat_trigger)
                or int(global_stall) >= int(self.params.global_stall_trigger)
                or (oracle is not None and float(oracle.get('avg_future_gain', 0.0)) > 0.03)
            )
        )
        return {'stats': stats, 'margin': float(margin), 'progress': float(progress), 'oracle': oracle, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_review or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, self.macros, max_macros=int(self.params.top_macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_review or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_stats = node_ctx['stats']
        current_margin = float(node_ctx['margin'])
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        family_best: dict[str, float] = {}
        raw = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            family = macro_family(cand)
            score = local_review_score(stats, current_margin, candidate_margin=cand_margin, reverse_need=reverse_need, family=family)
            if getattr(cand, 'source', 'primitive') == 'macro':
                score += float(self.params.macro_bonus)
            raw.append((cand, family, score))
            family_best[family] = max(float(family_best.get(family, -1e9)), float(score))
        top_families = {fam for fam, _ in sorted(family_best.items(), key=lambda item: item[1], reverse=True)[:2]}
        for cand, family, score in raw:
            delta = -float(self.params.review_bonus) * float(score)
            if family in top_families:
                delta -= float(self.params.family_bonus)
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
        accept_ratio = float(accepted_local) / max(float(valid_local), 1.0)
        event_hit = bool(
            float(node_ctx.get('margin', 1.0)) <= float(self.params.trigger_margin)
            or float(node_ctx.get('progress', 1.0)) <= float(self.params.progress_threshold)
            or accept_ratio <= float(self.params.accept_ratio_threshold)
        )
        update_global_stall(search_state, self.stall_slot, bool(event_hit))


def make_policy(memory: dict[str, Any], params: CX16CBLRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return BLRPolicy(case, bundle, params, memory, disable_review=bool(ablation.get('disable_review', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX16CBLRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx16_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX16CBLRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
