from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.heuristics import YawFieldHeuristic, compose_guidance
from planner.hybrid_astar import HybridAStarPlanner
from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx16.common import MacroPrimitive
from rs_cx23.common import class_key
from rs_cx24.common import FrozenHAATeacher, build_frozen_haa_teacher, make_haa_policy, trace_feature_vector
from rs_cx34.common import build_frozen_haa_stack
from rs_cx8.common import primitive_index_from_case, simulate_primitive_detailed


WITNESS_EXTRA_FEATURES = (
    'scene_focus_gap',
    'scene_barrier_peak',
    'scene_misc_like',
)


@dataclass(frozen=True)
class TypedMacroFamily:
    name: str
    macros: tuple[MacroPrimitive, ...]


@dataclass(frozen=True)
class FamilySupportStat:
    band: SupportBand
    avg_score: float
    hits: int


def reverse_pair_families() -> tuple[TypedMacroFamily, ...]:
    return (
        TypedMacroFamily(
            name='reverse_pair_left',
            macros=(
                MacroPrimitive('macro_rev_pair_l_hard', (1, 1), 'macro:reverse', 0.0, 0),
                MacroPrimitive('macro_rev_pair_l_soft', (3, 3), 'macro:reverse', 0.0, 0),
                MacroPrimitive('macro_rev_pair_l_mix12', (1, 3), 'macro:reverse', 0.0, 0),
                MacroPrimitive('macro_rev_pair_l_mix21', (3, 1), 'macro:reverse', 0.0, 0),
            ),
        ),
        TypedMacroFamily(
            name='reverse_pair_straight',
            macros=(
                MacroPrimitive('macro_rev_pair_s', (5, 5), 'macro:reverse', 0.0, 0),
            ),
        ),
        TypedMacroFamily(
            name='reverse_pair_right',
            macros=(
                MacroPrimitive('macro_rev_pair_r_soft', (7, 7), 'macro:reverse', 0.0, 0),
                MacroPrimitive('macro_rev_pair_r_hard', (9, 9), 'macro:reverse', 0.0, 0),
                MacroPrimitive('macro_rev_pair_r_mix12', (7, 9), 'macro:reverse', 0.0, 0),
                MacroPrimitive('macro_rev_pair_r_mix21', (9, 7), 'macro:reverse', 0.0, 0),
            ),
        ),
    )


def witness_feature_vector(case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any], search_state: dict[str, Any]) -> np.ndarray:
    base = trace_feature_vector(ctx, search_state, case, bundle)
    scene = dict(bundle.get('scene', {}))
    extra = np.asarray(
        [
            float(scene.get('focus_gap', 0.0)),
            float(scene.get('barrier_peak', 0.0)),
            float(scene.get('misc_likelihood', 0.0)),
        ],
        dtype=np.float32,
    )
    return np.concatenate([base.astype(np.float32), extra], axis=0).astype(np.float32)


def build_local_proxy(case: dict[str, Any], field: np.ndarray):
    planner = HybridAStarPlanner(
        occupancy=case['occupancy'],
        resolution=float(case['resolution']),
        vehicle_cfg=case['vehicle'],
        planner_cfg=case['planner_cfg'],
        esdf=case['esdf'],
    )
    anchor_fn = YawFieldHeuristic(
        field_3d=np.asarray(field, dtype=np.float32),
        resolution=float(case['resolution']),
        max_value=1e6,
        scale=1.0,
    )
    h_pair = compose_guidance(anchor_fn, None, planner.cfg.guidance_blend)
    return planner, h_pair


def best_macro_score_for_family(case: dict[str, Any], state: tuple[float, float, float], h_pair, family: TypedMacroFamily) -> tuple[float, MacroPrimitive | None]:
    pindex = primitive_index_from_case(case)
    max_steer = float(planner_max_steer(case))
    cur_anchor, _ = h_pair(float(state[0]), float(state[1]), float(state[2]))
    best_score = float('-inf')
    best_macro: MacroPrimitive | None = None
    for macro in family.macros:
        cur = tuple(float(v) for v in state)
        min_clearance = float('inf')
        valid = True
        for primitive_index in macro.primitive_indices:
            steer = float(pindex.actual_steer(int(primitive_index), max_steer))
            direction = int(pindex.actual_direction(int(primitive_index)))
            sim = simulate_primitive_detailed(case, cur, steer, direction)
            if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
                valid = False
                break
            min_clearance = min(min_clearance, float(sim.get('min_clearance', 0.0)))
            cur = tuple(float(v) for v in sim['next_state'])
        if not valid:
            continue
        next_anchor, _ = h_pair(float(cur[0]), float(cur[1]), float(cur[2]))
        score = float(cur_anchor - next_anchor) + 0.05 * float(max(min_clearance, 0.0))
        if score > best_score:
            best_score = float(score)
            best_macro = macro
    return float(best_score), best_macro


def planner_max_steer(case: dict[str, Any]) -> float:
    return float(np.deg2rad(float(case['vehicle'].max_steer_deg)))


def compile_typed_macro_support(
    calib_train_assets: list[dict[str, Any]],
    teacher: FrozenHAATeacher,
    *,
    families: tuple[TypedMacroFamily, ...],
    min_hits: int,
    out_dir: Path,
) -> dict[str, Any]:
    rows_by_family: dict[str, list[np.ndarray]] = {family.name: [] for family in families}
    scores_by_family: dict[str, list[float]] = {family.name: [] for family in families}
    chosen_rows: list[dict[str, Any]] = []

    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_haa_policy(teacher, case, bundle, field)
        planner, h_pair = build_local_proxy(case, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        for state in path[:-1]:
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]))
            ctx = policy.prepare_expand(
                planner=planner,
                record=rec,
                goal=tuple(map(float, case['goal'])),
                records=None,
                open_heap=None,
                anchor_heap=None,
                search_state=search_state,
                h_pair=h_pair,
            )
            if not isinstance(ctx, dict):
                continue
            if str(class_key(ctx)) != 'uncertain|none':
                continue
            feat = witness_feature_vector(case, bundle, ctx, search_state)
            scored: list[tuple[float, TypedMacroFamily, MacroPrimitive | None]] = []
            for family in families:
                score, macro = best_macro_score_for_family(case, tuple(map(float, state)), h_pair, family)
                if macro is None or not np.isfinite(score):
                    continue
                scored.append((float(score), family, macro))
            if not scored:
                continue
            scored.sort(key=lambda item: item[0], reverse=True)
            best_score, best_family, best_macro = scored[0]
            if best_macro is None or float(best_score) <= 0.0:
                continue
            rows_by_family[best_family.name].append(feat)
            scores_by_family[best_family.name].append(float(best_score))
            chosen_rows.append(
                {
                    'scenario': str(case['scenario']),
                    'family': str(best_family.name),
                    'macro_name': str(best_macro.name),
                    'score': float(best_score),
                    'sample_name': str(asset['path'].name),
                }
            )

    support: dict[str, FamilySupportStat] = {}
    for family in families:
        rows = rows_by_family[family.name]
        scores = scores_by_family[family.name]
        band = fit_support_band(rows, scores, low_q=0.05, high_q=0.95, sim_q=0.15)
        if band is None or len(rows) < int(max(min_hits, 1)):
            continue
        support[family.name] = FamilySupportStat(
            band=band,
            avg_score=float(np.mean(scores)) if scores else 0.0,
            hits=int(len(rows)),
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'typed_macro_support.json').write_text(
        json.dumps(
            {
                'families': {
                    family.name: {
                        'macros': [macro.__dict__ for macro in family.macros],
                        'hits': int(support[family.name].hits) if family.name in support else 0,
                        'avg_score': float(support[family.name].avg_score) if family.name in support else 0.0,
                    }
                    for family in families
                },
                'chosen_rows': chosen_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return {
        'families': families,
        'support': support,
    }


def choose_typed_family(
    case: dict[str, Any],
    bundle: dict[str, Any],
    node_ctx: dict[str, Any],
    search_state: dict[str, Any],
    h_pair,
    families: tuple[TypedMacroFamily, ...],
    support: dict[str, FamilySupportStat],
) -> tuple[str | None, list[MacroPrimitive], dict[str, float]]:
    feat = witness_feature_vector(case, bundle, node_ctx, search_state)
    state = (
        float(search_state.get('last_record_x', 0.0)),
        float(search_state.get('last_record_y', 0.0)),
        float(search_state.get('last_record_yaw', 0.0)),
    )
    scored: list[tuple[float, float, str, MacroPrimitive]] = []
    raw_scores: dict[str, float] = {}
    for family in families:
        score, macro = best_macro_score_for_family(case, state, h_pair, family)
        raw_scores[family.name] = float(score)
        stat = support.get(family.name, None)
        matched, sim = support_match(stat.band if stat is not None else None, feat, float(score), slack=0.0)
        if matched and macro is not None:
            scored.append((float(sim), float(score), family.name, macro))
    if not scored:
        return None, [], raw_scores
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    _, _, family_name, macro = scored[0]
    return str(family_name), [macro], raw_scores


__all__ = [
    'FamilySupportStat',
    'TypedMacroFamily',
    'WITNESS_EXTRA_FEATURES',
    'best_macro_score_for_family',
    'build_frozen_haa_stack',
    'build_local_proxy',
    'choose_typed_family',
    'compile_typed_macro_support',
    'reverse_pair_families',
    'witness_feature_vector',
]
