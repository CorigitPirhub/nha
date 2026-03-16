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
    extract_escape_motif_memory,
    increment_slot_counter,
    macro_successor_candidates,
    margin_key,
    primitive_family_from_index,
    read_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
    MacroPrimitive,
)


@dataclass(frozen=True)
class CX16DMECParams:
    trigger_margin: float
    repeat_trigger: int
    horizon_steps: int
    min_gain: float
    macro_bonus: float
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


def param_grid() -> list[CX16DMECParams]:
    return [
        CX16DMECParams(0.18, 1, 4, 0.08, 0.08, 0.08, 0.06, 0.22, 0.24, 0.30, 0.20, 0.10, 0.06, 0.08, 2, 2),
        CX16DMECParams(0.16, 1, 4, 0.10, 0.10, 0.10, 0.08, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2),
        CX16DMECParams(0.14, 2, 5, 0.12, 0.12, 0.12, 0.10, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Motif', 'disable_motif': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX16DMECParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    motifs = extract_escape_motif_memory(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=float(params.min_gain))
    serializable = {','.join(map(str, key)): {'sequence': list(value['sequence']), 'avg_gain': value['avg_gain'], 'hits': value['hits']} for key, value in motifs.items()}
    save_meta(out_dir / 'mec_meta.json', {'params': params.__dict__, 'motifs': serializable})
    return {'motifs': motifs, 'best_val_loss': float('nan')}


class MECPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX16DMECParams, memory: dict[str, Any], disable_motif: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_motif = bool(disable_motif)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.motifs = dict(memory.get('motifs', {})) if isinstance(memory, dict) else {}
        self.seen_slot = '_cx16_d_seen'
        self.stall_slot = '_cx16_d_stall'

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
        motif = None if self.disable_motif else self.motifs.get(tuple(key), None)
        seen = read_slot_counter(search_state, self.seen_slot, stats.key)
        active = bool(motif is not None and (float(margin) <= float(self.params.trigger_margin) or int(seen) >= int(self.params.repeat_trigger)))
        return {'stats': stats, 'margin': float(margin), 'motif': motif, 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_motif or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        motif = node_ctx.get('motif', None)
        if not isinstance(motif, dict):
            return []
        sequence = tuple(int(v) for v in motif.get('sequence', ()))
        if not sequence:
            return []
        macro = MacroPrimitive(
            name='motif_' + '_'.join(str(v) for v in sequence),
            primitive_indices=sequence,
            family='macro:motif',
            avg_gain=float(motif.get('avg_gain', 0.0)),
            hits=int(motif.get('hits', 0)),
        )
        return macro_successor_candidates(self.case, planner, record, h_pair, [macro], max_macros=1)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_motif or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        motif = node_ctx.get('motif', None)
        if not isinstance(motif, dict):
            return None
        current_stats = node_ctx['stats']
        current_margin = float(node_ctx['margin'])
        reverse_need = float(reverse_need_score(current_stats, self.spec))
        desired_seq = tuple(int(v) for v in motif.get('sequence', ()))
        desired_first_family = primitive_family_from_index(self.case, desired_seq[0]) if desired_seq else ''
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -0.18 * float(cand_margin - current_margin)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            is_matching_first = bool(
                desired_first_family
                and int(cand.primitive_index) >= 0
                and primitive_family_from_index(self.case, int(cand.primitive_index)) == desired_first_family
            )
            if is_matching_first:
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


def make_policy(memory: dict[str, Any], params: CX16DMECParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MECPolicy(case, bundle, params, memory, disable_motif=bool(ablation.get('disable_motif', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX16DMECParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx16_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX16DMECParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
