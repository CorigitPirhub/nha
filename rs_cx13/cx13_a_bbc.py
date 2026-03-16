from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx13.common import (
    BASELINE_CHOSEN_JSON,
    basin_decomposition,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    query_basin,
)


@dataclass(frozen=True)
class CX13ABBCParams:
    trap_thr: float
    corridor_thr: float
    min_cells: int
    trap_budget_base: int
    trap_budget_scale: float
    trap_penalty: float
    reverse_penalty: float
    corridor_bonus: float


def param_grid() -> list[CX13ABBCParams]:
    return [
        CX13ABBCParams(0.62, 0.55, 6, 6, 1.0, 0.18, 0.08, 0.04),
        CX13ABBCParams(0.60, 0.58, 8, 5, 0.9, 0.20, 0.10, 0.04),
        CX13ABBCParams(0.58, 0.60, 10, 4, 0.8, 0.24, 0.12, 0.05),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Budget', 'disable_budget': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX13ABBCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    guard_assets = list((dependencies or {}).get('guard_assets', []))
    stats = []
    for asset in guard_assets:
        basin_map, basin_meta = basin_decomposition(
            asset['case'],
            asset['bundle'],
            trap_thr=float(params.trap_thr),
            corridor_thr=float(params.corridor_thr),
            min_cells=int(params.min_cells),
            trap_budget_base=int(params.trap_budget_base),
            trap_budget_scale=float(params.trap_budget_scale),
        )
        stats.append({
            'sample_name': str(asset['path'].name),
            'num_trap_basins': int(sum(1 for v in basin_meta.values() if v.kind == 'trap')),
            'num_corridor_basins': int(sum(1 for v in basin_meta.values() if v.kind == 'corridor')),
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'bbc_meta.json').write_text(json.dumps({'guard_stats': stats[:20], 'num_guard_assets': len(stats)}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'best_val_loss': float('nan')}


class BBCPolicy:
    def __init__(self, case: dict[str, Any], basin_map: np.ndarray, basin_meta: dict[int, Any], params: CX13ABBCParams, disable_budget: bool = False) -> None:
        self.case = case
        self.basin_map = np.asarray(basin_map, dtype=np.int32)
        self.basin_meta = basin_meta
        self.params = params
        self.disable_budget = bool(disable_budget)
        self.state_key = '_cx13_bbc_counts'

    def _counts(self, search_state: dict[str, Any]) -> dict[int, int]:
        return search_state.setdefault(self.state_key, {})

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        basin_id = query_basin(self.case, self.basin_map, (float(record.x), float(record.y), float(record.yaw)))
        return {'basin_id': int(basin_id)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_budget:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        counts = self._counts(search_state)
        ranked = []
        for cand in candidates:
            basin_id = query_basin(self.case, self.basin_map, cand.next_state)
            meta = self.basin_meta.get(int(basin_id), None)
            delta = 0.0
            if meta is not None and meta.kind == 'trap':
                used = int(counts.get(int(basin_id), 0))
                overflow = max(used - int(meta.budget), 0)
                delta += float(self.params.trap_penalty) * (1.0 + float(overflow) / max(float(meta.budget), 1.0))
                if int(cand.direction) < 0:
                    delta += float(self.params.reverse_penalty)
            elif meta is not None and meta.kind == 'corridor':
                delta -= float(self.params.corridor_bonus) * (0.5 + float(meta.mean_score))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if self.disable_budget:
            return
        basin_id = int(node_ctx.get('basin_id', 0)) if isinstance(node_ctx, dict) else 0
        if basin_id == 0:
            return
        counts = self._counts(search_state)
        counts[basin_id] = int(counts.get(basin_id, 0)) + 1


def make_policy(memory: dict[str, Any], params: CX13ABBCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    basin_map, basin_meta = basin_decomposition(
        case,
        bundle,
        trap_thr=float(params.trap_thr),
        corridor_thr=float(params.corridor_thr),
        min_cells=int(params.min_cells),
        trap_budget_base=int(params.trap_budget_base),
        trap_budget_scale=float(params.trap_budget_scale),
    )
    return BBCPolicy(case, basin_map, basin_meta, params, disable_budget=bool(isinstance(ablation, dict) and ablation.get('disable_budget', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX13ABBCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = build_base_field(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX13ABBCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
