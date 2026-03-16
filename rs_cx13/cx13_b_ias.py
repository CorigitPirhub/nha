from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx13.common import (
    BASELINE_CHOSEN_JSON,
    ScheduleProfile,
    basin_decomposition,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    default_schedule_catalog,
    nearest_profile,
    query_basin,
    scene_feature_vector,
)


@dataclass(frozen=True)
class CX13BIASParams:
    trap_thr: float
    corridor_thr: float
    min_cells: int
    prototype_scale: float
    default_profile: str


def param_grid() -> list[CX13BIASParams]:
    return [
        CX13BIASParams(0.60, 0.56, 8, 1.0, 'balanced'),
        CX13BIASParams(0.58, 0.58, 8, 1.0, 'cautious'),
        CX13BIASParams(0.62, 0.55, 6, 1.0, 'balanced'),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'Always-Balanced', 'force_profile': 'balanced'}]


def _label_profile(scene_feat: np.ndarray) -> str:
    hard, misc, bridge, openness, trap_mean, trap_max, corridor_mean, corridor_max, num_trap, num_corr, trap_area, corr_area = map(float, scene_feat)
    if trap_area > 0.08 or trap_max > 0.75:
        return 'cautious'
    if hard > misc + 0.05 and corr_area > trap_area:
        return 'exploratory'
    return 'balanced'


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX13BIASParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    guard_assets = list((dependencies or {}).get('guard_assets', []))
    prototypes: dict[str, list[np.ndarray]] = {}
    for asset in guard_assets:
        basin_map, basin_meta = basin_decomposition(
            asset['case'],
            asset['bundle'],
            trap_thr=float(params.trap_thr),
            corridor_thr=float(params.corridor_thr),
            min_cells=int(params.min_cells),
            trap_budget_base=6,
            trap_budget_scale=1.0,
        )
        feat = scene_feature_vector(asset['case'], asset['bundle'], basin_map, basin_meta)
        label = _label_profile(feat)
        prototypes.setdefault(label, []).append(feat.astype(np.float32))
    proto_bank = {k: np.mean(np.stack(v, axis=0), axis=0).astype(np.float32) for k, v in prototypes.items() if v}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'ias_meta.json').write_text(json.dumps({'labels': {k: len(v) for k, v in prototypes.items()}, 'default_profile': params.default_profile}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'prototypes': proto_bank, 'best_val_loss': float('nan')}


class IASPolicy:
    def __init__(self, case: dict[str, Any], basin_map: np.ndarray, basin_meta: dict[int, Any], profile: ScheduleProfile) -> None:
        self.case = case
        self.basin_map = np.asarray(basin_map, dtype=np.int32)
        self.basin_meta = basin_meta
        self.profile = profile
        self.count_key = '_cx13_ias_counts'

    def _counts(self, search_state: dict[str, Any]) -> dict[int, int]:
        return search_state.setdefault(self.count_key, {})

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        phase = 0 if int(record.depth) < int(self.profile.switch_depth) else 1
        return {'phase': int(phase)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        phase = int(node_ctx.get('phase', 0)) if isinstance(node_ctx, dict) else 0
        trap_penalty = float(self.profile.trap_penalty_early if phase == 0 else self.profile.trap_penalty_late)
        reverse_penalty = float(self.profile.reverse_penalty_early if phase == 0 else self.profile.reverse_penalty_late)
        counts = self._counts(search_state)
        ranked = []
        for cand in candidates:
            basin_id = query_basin(self.case, self.basin_map, cand.next_state)
            meta = self.basin_meta.get(int(basin_id), None)
            delta = 0.0
            if meta is not None and meta.kind == 'trap':
                budget = max(1, int(round(float(meta.budget) * float(self.profile.trap_budget_scale))))
                used = int(counts.get(int(basin_id), 0))
                if used >= budget:
                    delta += trap_penalty
                if int(cand.direction) < 0:
                    delta += reverse_penalty
            elif meta is not None and meta.kind == 'corridor':
                delta -= float(self.profile.corridor_bonus) * (0.5 + float(meta.mean_score))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        basin_id = query_basin(self.case, self.basin_map, (float(record.x), float(record.y), float(record.yaw)))
        if basin_id == 0:
            return
        counts = self._counts(search_state)
        counts[basin_id] = int(counts.get(basin_id, 0)) + 1


def make_policy(memory: dict[str, Any], params: CX13BIASParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    basin_map, basin_meta = basin_decomposition(
        case,
        bundle,
        trap_thr=float(params.trap_thr),
        corridor_thr=float(params.corridor_thr),
        min_cells=int(params.min_cells),
        trap_budget_base=6,
        trap_budget_scale=1.0,
    )
    scene_feat = scene_feature_vector(case, bundle, basin_map, basin_meta)
    catalog = {profile.name: profile for profile in default_schedule_catalog()}
    if isinstance(ablation, dict) and ablation.get('force_profile', None) is not None:
        profile = catalog[str(ablation['force_profile'])]
    else:
        name = nearest_profile(scene_feat, memory.get('prototypes', {}), params.default_profile)
        profile = catalog.get(str(name), catalog[str(params.default_profile)])
    return IASPolicy(case, basin_map, basin_meta, profile)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX13BIASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = build_base_field(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX13BIASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
