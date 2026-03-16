from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx9.common import (
    accepted_cx3d_nonholonomic,
    accepted_cx3d_standard,
    active_gate_mode,
    collect_mode_training_rows,
    fit_mode_prototypes,
    primitive_priority_delta,
    select_program_gates,
)


@dataclass(frozen=True)
class CX9BCSPParams:
    top_k: int
    gate_threshold: float
    reach_thr_m: float
    mode_strength: float


def param_grid() -> list[CX9BCSPParams]:
    return [
        CX9BCSPParams(1, 0.42, 1.5, 0.30),
        CX9BCSPParams(2, 0.40, 1.8, 0.34),
        CX9BCSPParams(2, 0.48, 2.2, 0.40),
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX9BCSPParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = collect_mode_training_rows(calib_train_assets)
    proto_bank = fit_mode_prototypes(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'program_meta.json').write_text(
        __import__('json').dumps({'counts': proto_bank.get('counts', {}), 'num_rows': len(rows)}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return {'prototype_bank': proto_bank, 'train_rows': int(len(rows)), 'best_val_loss': float('nan')}


class CSPPolicy:
    def __init__(self, case: dict[str, Any], gates: list[dict[str, Any]], params: CX9BCSPParams) -> None:
        self.case = case
        self.gates = list(gates)
        self.params = params

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        mode = active_gate_mode(self.gates, state, reached_thr_m=float(self.params.reach_thr_m))
        return {'mode': int(mode)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), mode, float(self.params.mode_strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX9BCSPParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    gates = select_program_gates(case, bundle, field, memory.get('prototype_bank', {}), top_k=int(params.top_k), gate_threshold=float(params.gate_threshold))
    policy = CSPPolicy(case, gates, params)
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX9BCSPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX9BCSPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)
