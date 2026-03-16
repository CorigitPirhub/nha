from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx15.common import (
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    increment_slot_counter,
    primitive_family,
    primitive_group,
    read_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)


@dataclass(frozen=True)
class CX15BEMRParams:
    trigger_margin: float
    stall_threshold: float
    accept_ratio_threshold: float
    repeat_trigger: int
    global_stall_trigger: int
    improve_gain: float
    family_bonus: float
    reverse_bonus: float
    top_families: int
    clearance_w: float
    corridor_w: float
    trap_w: float
    reverse_w: float
    lateral_w: float
    forward_w: float
    heading_w: float
    stride_cells: int
    yaw_stride: int


def param_grid() -> list[CX15BEMRParams]:
    return [
        CX15BEMRParams(0.18, 0.010, 0.28, 1, 1, 0.24, 0.08, 0.08, 2, 0.24, 0.22, 0.28, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15BEMRParams(0.16, 0.012, 0.25, 1, 2, 0.26, 0.10, 0.10, 2, 0.22, 0.24, 0.30, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15BEMRParams(0.14, 0.015, 0.22, 2, 2, 0.28, 0.12, 0.10, 2, 0.22, 0.24, 0.32, 0.20, 0.10, 0.06, 0.08, 2, 2),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'Always-Trigger', 'disable_trigger': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX15BEMRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    save_meta(out_dir / 'emr_meta.json', {'params': params.__dict__})
    return {'best_val_loss': float('nan')}


class EMRPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX15BEMRParams, disable_trigger: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_trigger = bool(disable_trigger)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.seen_slot = '_cx15_b_seen'
        self.stall_slot = '_cx15_b_global_stall'

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
        progress = float(getattr(record, 'anchor', 0.0) - float(records[record.parent].anchor)) if getattr(record, 'parent', None) in records else 0.0
        seen = read_slot_counter(search_state, self.seen_slot, stats.key)
        global_stall = int(search_state.get(self.stall_slot, 0))
        active = bool(self.disable_trigger)
        if not active:
            active = bool(
                float(margin) <= float(self.params.trigger_margin)
                or float(progress) <= float(self.params.stall_threshold)
                or int(seen) >= int(self.params.repeat_trigger)
                or int(global_stall) >= int(self.params.global_stall_trigger)
            )
        return {'stats': stats, 'margin': float(margin), 'progress': float(progress), 'active': bool(active)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_stats = node_ctx['stats']
        current_margin = float(node_ctx['margin'])
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        family_scores: dict[str, float] = {}
        family_rows = []
        for cand, stats in zip(candidates, cand_stats):
            margin = self._margin(stats)
            improve = float(margin - current_margin)
            fam = primitive_family(cand)
            score = float(margin) + float(self.params.improve_gain) * improve
            if float(reverse_need) > 0.08 and int(cand.direction) < 0:
                score += float(self.params.reverse_bonus)
            family_scores[fam] = max(float(family_scores.get(fam, -1e9)), float(score))
            family_rows.append((cand, stats, fam, float(score)))
        ranked_families = sorted(family_scores.items(), key=lambda item: item[1], reverse=True)
        keep = {fam for fam, _ in ranked_families[: int(max(self.params.top_families, 1))]}
        ranked = []
        for cand, stats, fam, score in family_rows:
            delta = -float(score)
            if fam in keep:
                delta -= float(self.params.family_bonus)
            elif primitive_group(fam) == 'forward_turn':
                delta += 0.02
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
            or float(node_ctx.get('progress', 1.0)) <= float(self.params.stall_threshold)
            or accept_ratio <= float(self.params.accept_ratio_threshold)
        )
        update_global_stall(search_state, self.stall_slot, bool(event_hit))


def make_policy(memory: dict[str, Any], params: CX15BEMRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return EMRPolicy(case, bundle, params, disable_trigger=bool(ablation.get('disable_trigger', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX15BEMRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx15_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX15BEMRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
