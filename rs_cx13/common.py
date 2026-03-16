from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import run_hybrid_with_policy
from rs_cx11.common import fit_tree, predict_tree, tree_to_dict
from rs_cx9.common import select_bottleneck_windows

BASELINE_CHOSEN_JSON = Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json')

SCENE_FEATURE_NAMES = (
    'hard_likelihood',
    'misc_likelihood',
    'bridge_diffuse',
    'path_openness',
    'trap_mean',
    'trap_max',
    'corridor_mean',
    'corridor_max',
    'num_trap_basins',
    'num_corridor_basins',
    'trap_area_ratio',
    'corridor_area_ratio',
)


@dataclass(frozen=True)
class BasinInfo:
    basin_id: int
    kind: str
    area_cells: int
    mean_score: float
    budget: int


@dataclass(frozen=True)
class ScheduleProfile:
    name: str
    switch_depth: int
    trap_penalty_early: float
    trap_penalty_late: float
    reverse_penalty_early: float
    reverse_penalty_late: float
    corridor_bonus: float
    trap_budget_scale: float


@dataclass(frozen=True)
class TicketInfo:
    ticket_id: int
    state: tuple[float, float, float]
    radius_m: float
    reserve_budget: int
    overrun_penalty: float
    reverse_quota: int
    score: float


def load_base_params(chosen_json: Path = BASELINE_CHOSEN_JSON) -> dict[str, Any]:
    return json.loads(Path(chosen_json).read_text(encoding='utf-8'))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg) -> tuple[dict[str, Any], np.ndarray]:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return bundle, np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return np.asarray(field, dtype=np.float32)


def trap_score_map(bundle: dict[str, Any]) -> np.ndarray:
    barrier = np.asarray(bundle['barrier'], dtype=np.float32)
    focus = np.asarray(bundle['focus'], dtype=np.float32)
    corridor = np.asarray(bundle['corridor'], dtype=np.float32)
    risk = np.asarray(bundle.get('risk', np.zeros_like(barrier)), dtype=np.float32)
    score = 0.40 * barrier + 0.25 * focus + 0.20 * (1.0 - corridor) + 0.15 * risk
    score = score.astype(np.float32)
    lo = float(np.min(score))
    hi = float(np.max(score))
    if hi <= lo + 1e-6:
        return np.zeros_like(score, dtype=np.float32)
    return ((score - lo) / (hi - lo)).astype(np.float32)


def corridor_score_map(bundle: dict[str, Any]) -> np.ndarray:
    barrier = np.asarray(bundle['barrier'], dtype=np.float32)
    focus = np.asarray(bundle['focus'], dtype=np.float32)
    corridor = np.asarray(bundle['corridor'], dtype=np.float32)
    score = 0.55 * corridor + 0.25 * focus + 0.20 * (1.0 - barrier)
    score = score.astype(np.float32)
    lo = float(np.min(score))
    hi = float(np.max(score))
    if hi <= lo + 1e-6:
        return np.zeros_like(score, dtype=np.float32)
    return ((score - lo) / (hi - lo)).astype(np.float32)


def basin_decomposition(
    case: dict[str, Any],
    bundle: dict[str, Any],
    *,
    trap_thr: float,
    corridor_thr: float,
    min_cells: int,
    trap_budget_base: int,
    trap_budget_scale: float,
) -> tuple[np.ndarray, dict[int, BasinInfo]]:
    occupancy = np.asarray(case['occupancy'], dtype=bool)
    trap_map = trap_score_map(bundle)
    corridor_map = corridor_score_map(bundle)
    basin_map = np.zeros_like(occupancy, dtype=np.int32)
    meta: dict[int, BasinInfo] = {}
    next_id = 1

    for kind, score_map, thr in [('trap', trap_map, trap_thr), ('corridor', corridor_map, corridor_thr)]:
        mask = (score_map >= float(thr)) & (~occupancy)
        labeled, num = ndimage.label(mask.astype(np.int32))
        for idx in range(1, int(num) + 1):
            comp = labeled == idx
            area = int(np.sum(comp))
            if area < int(min_cells):
                continue
            mean_score = float(np.mean(score_map[comp]))
            budget = int(max(1, round(float(trap_budget_base) + float(trap_budget_scale) * math.sqrt(float(area)) * (0.5 + mean_score))))
            basin_id = int(next_id if kind == 'corridor' else -next_id)
            basin_map[comp] = basin_id
            meta[basin_id] = BasinInfo(
                basin_id=basin_id,
                kind=kind,
                area_cells=area,
                mean_score=mean_score,
                budget=budget,
            )
            next_id += 1
    return basin_map.astype(np.int32), meta


def query_basin(case: dict[str, Any], basin_map: np.ndarray, state: tuple[float, float, float]) -> int:
    x, y, _ = state
    res = float(case['resolution'])
    gx = int(np.clip(np.floor(float(x) / max(res, 1e-6)), 0, basin_map.shape[1] - 1))
    gy = int(np.clip(np.floor(float(y) / max(res, 1e-6)), 0, basin_map.shape[0] - 1))
    return int(basin_map[gy, gx])


def scene_feature_vector(case: dict[str, Any], bundle: dict[str, Any], basin_map: np.ndarray, basin_meta: dict[int, BasinInfo]) -> np.ndarray:
    scene = bundle.get('scene', {})
    trap_ids = [k for k, v in basin_meta.items() if v.kind == 'trap']
    corr_ids = [k for k, v in basin_meta.items() if v.kind == 'corridor']
    total_free = int(np.sum(~np.asarray(case['occupancy'], dtype=bool)))
    trap_cells = int(np.sum(np.isin(basin_map, trap_ids))) if trap_ids else 0
    corr_cells = int(np.sum(np.isin(basin_map, corr_ids))) if corr_ids else 0
    return np.asarray([
        float(scene.get('hard_likelihood', 0.0)),
        float(scene.get('misc_likelihood', 0.0)),
        float(scene.get('bridge_diffuse', 0.0)),
        float(scene.get('path_openness', 0.0)),
        float(np.mean([basin_meta[k].mean_score for k in trap_ids])) if trap_ids else 0.0,
        float(np.max([basin_meta[k].mean_score for k in trap_ids])) if trap_ids else 0.0,
        float(np.mean([basin_meta[k].mean_score for k in corr_ids])) if corr_ids else 0.0,
        float(np.max([basin_meta[k].mean_score for k in corr_ids])) if corr_ids else 0.0,
        float(len(trap_ids)),
        float(len(corr_ids)),
        float(trap_cells / max(total_free, 1)),
        float(corr_cells / max(total_free, 1)),
    ], dtype=np.float32)


def default_schedule_catalog() -> list[ScheduleProfile]:
    return [
        ScheduleProfile('cautious', 0, 0.35, 0.45, 0.20, 0.25, 0.00, 0.70),
        ScheduleProfile('balanced', 4, 0.10, 0.28, 0.05, 0.18, 0.04, 1.00),
        ScheduleProfile('exploratory', 6, 0.00, 0.20, 0.00, 0.12, 0.08, 1.35),
    ]


def nearest_profile(scene_feat: np.ndarray, prototypes: dict[str, np.ndarray], default_name: str) -> str:
    if not prototypes:
        return str(default_name)
    feat = np.asarray(scene_feat, dtype=np.float32)
    best_name = str(default_name)
    best_dist = float('inf')
    for name, proto in prototypes.items():
        dist = float(np.linalg.norm(feat - np.asarray(proto, dtype=np.float32)))
        if dist < best_dist:
            best_dist = dist
            best_name = str(name)
    return best_name


def extract_tickets(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    *,
    top_k: int,
    radius_m: float,
    reserve_budget: int,
    overrun_penalty: float,
    reverse_quota: int,
) -> list[TicketInfo]:
    windows = select_bottleneck_windows(case, bundle, field, top_k=int(top_k), min_sep_m=max(float(radius_m), 1.0), gate_threshold=0.40)
    tickets = []
    for idx, win in enumerate(windows, start=1):
        score = float(win.get('score', 0.0))
        tickets.append(TicketInfo(
            ticket_id=int(idx),
            state=tuple(float(v) for v in win['state']),
            radius_m=float(radius_m),
            reserve_budget=int(max(1, round(float(reserve_budget) * (0.5 + score)))),
            overrun_penalty=float(overrun_penalty),
            reverse_quota=int(reverse_quota),
            score=score,
        ))
    return tickets


def query_ticket(tickets: list[TicketInfo], state: tuple[float, float, float]) -> int:
    x, y, _ = state
    best_id = 0
    best_dist = float('inf')
    for ticket in tickets:
        tx, ty, _ = ticket.state
        dist = float(math.hypot(float(tx) - float(x), float(ty) - float(y)))
        if dist <= float(ticket.radius_m) and dist < best_dist:
            best_id = int(ticket.ticket_id)
            best_dist = dist
    return int(best_id)


def compare_plan_to_baseline(baseline, plan, prep_ms: float = 0.0) -> dict[str, float]:
    total_ms = float(getattr(plan, 'runtime_ms', 0.0)) + float(prep_ms)
    return {
        'success_delta': float(getattr(plan, 'success', 0.0)) - float(getattr(baseline, 'success', 0.0)),
        'exp_delta': float(getattr(baseline, 'expansions', 0.0)) - float(getattr(plan, 'expansions', 0.0)),
        'time_delta_ms': float(getattr(baseline, 'runtime_ms', 0.0)) - float(total_ms),
        'time_overhead_ratio': (float(total_ms) - float(getattr(baseline, 'runtime_ms', 0.0))) / max(float(getattr(baseline, 'runtime_ms', 0.0)), 1e-6),
    }


def standard_identity_error(sample, predictor, field_builder) -> float:
    _, accepted = accepted_cx3d_standard(sample, predictor)
    field = field_builder(sample, predictor)
    return float(np.max(np.abs(np.asarray(field, dtype=np.float32) - np.asarray(accepted, dtype=np.float32))))


__all__ = [
    'BASELINE_CHOSEN_JSON',
    'BasinInfo',
    'SCENE_FEATURE_NAMES',
    'ScheduleProfile',
    'TicketInfo',
    'basin_decomposition',
    'build_nonholonomic_field',
    'build_standard_field',
    'compare_plan_to_baseline',
    'corridor_score_map',
    'default_schedule_catalog',
    'extract_tickets',
    'fit_tree',
    'load_base_params',
    'nearest_profile',
    'predict_tree',
    'query_basin',
    'query_ticket',
    'run_hybrid_with_policy',
    'scene_feature_vector',
    'standard_identity_error',
    'trap_score_map',
    'tree_to_dict',
]
