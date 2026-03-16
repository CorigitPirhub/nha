from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx20.common import (
    FoundationState,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    compile_viability_table,
    foundation_state,
    margin_key,
    query_viability_table,
    save_meta,
)


@dataclass(frozen=True)
class CX20AMVFParams:
    cost_gain: float
    viability_gain: float
    reverse_gain: float
    trap_escape_gain: float
    oracle_gain: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX20AMVFParams]:
    return [
        CX20AMVFParams(0.02, 0.10, 0.06, 0.04, 0.04, 2, 2, 5),
        CX20AMVFParams(0.02, 0.12, 0.08, 0.05, 0.05, 2, 2, 5),
        CX20AMVFParams(0.02, 0.14, 0.10, 0.06, 0.06, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-MultiHead', 'disable_multihead': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX20AMVFParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    save_meta(out_dir / 'mvf_meta.json', {'params': params.__dict__, 'viability_table_size': int(len(table))})
    return {'viability_table': table, 'best_val_loss': float('nan')}


class MVFPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX20AMVFParams, memory: dict[str, Any], disable_multihead: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_multihead = bool(disable_multihead)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}

    def _score(self, f: FoundationState, oracle_gain: float) -> float:
        return float(
            float(self.params.cost_gain) * float(f.cost_to_go)
            - float(self.params.viability_gain) * float(f.viability)
            - float(self.params.reverse_gain) * float(f.reverse_required)
            - float(self.params.trap_escape_gain) * float(f.trap_escape_affinity)
            - float(self.params.oracle_gain) * float(oracle_gain)
        )

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_multihead:
            return None
        ranked = []
        for cand in candidates:
            f = foundation_state(self.case, self.case.get('_cx20_bundle', {}), self.field, self.encoder, cand.next_state, self.spec)
            stats = self.encoder.features(cand.next_state)
            oracle = query_viability_table(self.table, margin_key(stats))
            oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
            ranked.append((cand, {'priority_secondary_delta': float(self._score(f, oracle_gain))}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX20AMVFParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MVFPolicy(case, bundle, field, params, memory, disable_multihead=bool(ablation.get('disable_multihead', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX20AMVFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx20_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX20AMVFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
