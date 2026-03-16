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
    macro_family,
    macro_successor_candidates,
    recoverability_margin,
    reverse_need_score,
    save_meta,
)


@dataclass(frozen=True)
class CX16ANMLParams:
    macro_gate: float
    reverse_need_thr: float
    top_macros: int
    macro_bonus: float
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


def param_grid() -> list[CX16ANMLParams]:
    return [
        CX16ANMLParams(0.18, 0.08, 2, 0.06, 0.18, 0.22, 0.24, 0.30, 0.20, 0.10, 0.06, 0.08, 2, 2, 4),
        CX16ANMLParams(0.16, 0.08, 3, 0.08, 0.20, 0.22, 0.24, 0.32, 0.22, 0.10, 0.06, 0.08, 2, 2, 4),
        CX16ANMLParams(0.14, 0.06, 3, 0.10, 0.22, 0.20, 0.26, 0.34, 0.22, 0.10, 0.04, 0.08, 2, 2, 5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Macro-Library', 'disable_macros': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX16ANMLParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=int(params.top_macros))
    save_meta(out_dir / 'nml_meta.json', {'params': params.__dict__, 'macros': [m.__dict__ for m in macros]})
    return {'macros': macros, 'best_val_loss': float('nan')}


class NMLPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX16ANMLParams, memory: dict[str, Any], disable_macros: bool = False) -> None:
        self.case = case
        self.params = params
        self.disable_macros = bool(disable_macros)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []

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
        reverse_need = float(reverse_need_score(stats, self.spec))
        active = bool((not self.disable_macros) and (float(margin) <= float(self.params.macro_gate) or float(reverse_need) >= float(self.params.reverse_need_thr)))
        return {'stats': stats, 'margin': float(margin), 'reverse_need': float(reverse_need), 'active': bool(active)}

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_macros or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, self.macros, max_macros=int(self.params.top_macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_macros or not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        current_margin = float(node_ctx.get('margin', 0.0))
        cand_stats = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, stats in zip(candidates, cand_stats):
            cand_margin = self._margin(stats)
            delta = -float(self.params.improve_gain) * float(cand_margin - current_margin)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            elif 'reverse' in macro_family(cand):
                delta += 0.02
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX16ANMLParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return NMLPolicy(case, bundle, params, memory, disable_macros=bool(ablation.get('disable_macros', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX16ANMLParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx16_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX16ANMLParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
