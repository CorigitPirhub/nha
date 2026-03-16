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
    extract_escape_motifs,
    increment_slot_counter,
    margin_key,
    primitive_family,
    read_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)


@dataclass(frozen=True)
class CX15CFMEParams:
    trap_threshold: float
    min_escape_gain: float
    horizon_steps: int
    trigger_margin: float
    repeat_trigger: int
    family_bonus: float
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


def param_grid() -> list[CX15CFMEParams]:
    return [
        CX15CFMEParams(0.52, 0.10, 3, 0.18, 1, 0.10, 0.06, 0.24, 0.22, 0.28, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15CFMEParams(0.48, 0.12, 4, 0.16, 1, 0.12, 0.08, 0.22, 0.24, 0.30, 0.18, 0.10, 0.08, 0.08, 2, 2),
        CX15CFMEParams(0.44, 0.14, 4, 0.14, 2, 0.14, 0.10, 0.22, 0.24, 0.32, 0.20, 0.10, 0.06, 0.08, 2, 2),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Memory', 'disable_memory': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX15CFMEParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    motifs = extract_escape_motifs(
        calib_train_assets,
        spec,
        trap_threshold=float(params.trap_threshold),
        min_gain=float(params.min_escape_gain),
        horizon_steps=int(params.horizon_steps),
    )
    serializable = {','.join(map(str, key)): value for key, value in motifs.items()}
    save_meta(out_dir / 'fme_meta.json', {'params': params.__dict__, 'motifs': serializable})
    return {'motifs': motifs, 'best_val_loss': float('nan')}


class FMEPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX15CFMEParams, motifs: dict[tuple[int, ...], dict[str, Any]], disable_memory: bool = False) -> None:
        self.case = case
        self.params = params
        self.motifs = motifs
        self.disable_memory = bool(disable_memory)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.seen_slot = '_cx15_c_seen'
        self.stall_slot = '_cx15_c_stall'

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
        key = margin_key(stats)
        margin = self._margin(stats)
        seen = read_slot_counter(search_state, self.seen_slot, stats.key)
        motif = None if self.disable_memory else self.motifs.get(tuple(key), None)
        active = bool(motif is not None and (float(margin) <= float(self.params.trigger_margin) or int(seen) >= int(self.params.repeat_trigger)))
        return {'stats': stats, 'memory_key': tuple(key), 'motif': motif, 'active': bool(active), 'margin': float(margin)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        motif = node_ctx.get('motif', None)
        if not isinstance(motif, dict):
            return None
        desired_family = str(motif.get('family', ''))
        current_stats = node_ctx['stats']
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        current_margin = float(node_ctx.get('margin', 0.0))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            fam = primitive_family(cand)
            margin = self._margin(stats)
            delta = -0.20 * float(margin - current_margin)
            if fam == desired_family:
                delta -= float(self.params.family_bonus)
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
        event_hit = bool(int(accepted_local) == 0 or float(node_ctx.get('margin', 1.0)) <= float(self.params.trigger_margin))
        update_global_stall(search_state, self.stall_slot, bool(event_hit))


def make_policy(memory: dict[str, Any], params: CX15CFMEParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    motifs = dict(memory.get('motifs', {})) if isinstance(memory, dict) else {}
    return FMEPolicy(case, bundle, params, motifs, disable_memory=bool(ablation.get('disable_memory', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX15CFMEParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx15_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX15CFMEParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
