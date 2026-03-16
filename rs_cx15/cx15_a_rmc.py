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
    read_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)


@dataclass(frozen=True)
class CX15ARMCParams:
    margin_gate: float
    hopeless_margin: float
    reverse_need_thr: float
    repeat_trigger: int
    improve_gain: float
    reverse_bonus: float
    trap_penalty: float
    hopeless_penalty: float
    clearance_w: float
    corridor_w: float
    trap_w: float
    reverse_w: float
    lateral_w: float
    forward_w: float
    heading_w: float
    stride_cells: int
    yaw_stride: int


def param_grid() -> list[CX15ARMCParams]:
    return [
        CX15ARMCParams(0.20, 0.04, 0.10, 1, 0.24, 0.10, 0.08, 0.08, 0.24, 0.22, 0.28, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15ARMCParams(0.18, 0.03, 0.08, 1, 0.28, 0.12, 0.10, 0.10, 0.22, 0.24, 0.30, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15ARMCParams(0.16, 0.02, 0.08, 2, 0.30, 0.14, 0.12, 0.12, 0.22, 0.24, 0.32, 0.20, 0.10, 0.06, 0.08, 2, 2),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Recoverability', 'disable_recoverability': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX15ARMCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    save_meta(out_dir / 'rmc_meta.json', {'params': params.__dict__})
    return {'best_val_loss': float('nan')}


class RMCPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX15ARMCParams, disable_recoverability: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_recoverability = bool(disable_recoverability)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.seen_slot = '_cx15_a_seen'
        self.stall_slot = '_cx15_a_global_stall'

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
        seen = read_slot_counter(search_state, self.seen_slot, stats.key)
        active = bool(
            (not self.disable_recoverability)
            and (
                float(margin) <= float(self.params.margin_gate)
                or float(reverse_need_score(stats, self.spec)) >= float(self.params.reverse_need_thr)
                or int(seen) >= int(self.params.repeat_trigger)
            )
        )
        return {'stats': stats, 'margin': float(margin), 'active': bool(active)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_recoverability or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_stats = node_ctx['stats']
        current_margin = float(node_ctx['margin'])
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            margin = self._margin(stats)
            improve = float(margin - current_margin)
            delta = -float(self.params.improve_gain) * improve
            if float(reverse_need) >= float(self.params.reverse_need_thr) and int(cand.direction) < 0:
                delta -= float(self.params.reverse_bonus)
            delta += float(self.params.trap_penalty) * max(0.0, float(stats.trap - current_stats.trap))
            if float(margin) <= float(self.params.hopeless_margin):
                delta += float(self.params.hopeless_penalty)
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
        event_hit = int(accepted_local) == 0 or float(node_ctx.get('margin', 0.0)) <= float(self.params.margin_gate)
        update_global_stall(search_state, self.stall_slot, bool(event_hit))


def make_policy(memory: dict[str, Any], params: CX15ARMCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return RMCPolicy(case, bundle, params, disable_recoverability=bool(ablation.get('disable_recoverability', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX15ARMCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx15_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX15ARMCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
