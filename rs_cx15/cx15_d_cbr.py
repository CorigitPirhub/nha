from __future__ import annotations

import math
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
    current_progress,
    increment_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)


@dataclass(frozen=True)
class CX15DCBRParams:
    depression_margin: float
    stall_threshold: float
    accept_ratio_threshold: float
    repeat_trigger: int
    border_radius: int
    alignment_bonus: float
    improvement_bonus: float
    reverse_bonus: float
    clearance_w: float
    corridor_w: float
    trap_w: float
    reverse_w: float
    lateral_w: float
    forward_w: float
    heading_w: float
    stride_cells: int
    yaw_stride: int


def param_grid() -> list[CX15DCBRParams]:
    return [
        CX15DCBRParams(0.18, 0.010, 0.28, 1, 2, 0.10, 0.18, 0.06, 0.24, 0.22, 0.28, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15DCBRParams(0.16, 0.012, 0.25, 1, 2, 0.12, 0.20, 0.08, 0.22, 0.24, 0.30, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15DCBRParams(0.14, 0.015, 0.22, 2, 3, 0.14, 0.22, 0.10, 0.22, 0.24, 0.32, 0.20, 0.10, 0.06, 0.08, 2, 2),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Border-Repair', 'disable_border': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX15DCBRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    save_meta(out_dir / 'cbr_meta.json', {'params': params.__dict__})
    return {'best_val_loss': float('nan')}


class CBRPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX15DCBRParams, disable_border: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_border = bool(disable_border)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.seen_slot = '_cx15_d_seen'
        self.stall_slot = '_cx15_d_stall'

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
        progress = current_progress(self.case, self.field, record, records, depth=1)
        seen = int(search_state.get(self.seen_slot, {}).get(stats.key, 0)) if isinstance(search_state.get(self.seen_slot, None), dict) else 0
        active = bool(
            (not self.disable_border)
            and (
                float(margin) <= float(self.params.depression_margin)
                or float(progress) <= float(self.params.stall_threshold)
                or int(seen) >= int(self.params.repeat_trigger)
            )
        )
        target_key = self.encoder.best_border_key(stats.key, int(self.params.border_radius)) if active else None
        target_vec = None
        if target_key is not None:
            cx, cy, _ = self.encoder.bucket_center(stats.key)
            tx, ty, _ = self.encoder.bucket_center(target_key)
            target_vec = (float(tx - cx), float(ty - cy))
        return {'stats': stats, 'margin': float(margin), 'active': bool(active and target_vec is not None), 'target_vec': target_vec, 'progress': float(progress)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_stats = node_ctx['stats']
        current_margin = float(node_ctx['margin'])
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        target_vec = node_ctx.get('target_vec', None)
        if target_vec is None:
            return None
        tx, ty = map(float, target_vec)
        target_norm = float(math.hypot(tx, ty))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            margin = self._margin(stats)
            improve = float(margin - current_margin)
            move_dx = float(cand.next_state[0] - float(record.x))
            move_dy = float(cand.next_state[1] - float(record.y))
            move_norm = float(math.hypot(move_dx, move_dy))
            align = 0.0 if move_norm <= 1e-6 or target_norm <= 1e-6 else float((move_dx * tx + move_dy * ty) / (move_norm * target_norm))
            delta = -float(self.params.improvement_bonus) * improve - float(self.params.alignment_bonus) * align
            if float(reverse_need) > 0.08 and int(cand.direction) < 0:
                delta -= float(self.params.reverse_bonus)
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
            float(node_ctx.get('margin', 1.0)) <= float(self.params.depression_margin)
            or float(node_ctx.get('progress', 1.0)) <= float(self.params.stall_threshold)
            or accept_ratio <= float(self.params.accept_ratio_threshold)
        )
        update_global_stall(search_state, self.stall_slot, bool(event_hit))


def make_policy(memory: dict[str, Any], params: CX15DCBRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CBRPolicy(case, bundle, field, params, disable_border=bool(ablation.get('disable_border', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX15DCBRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx15_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX15DCBRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
