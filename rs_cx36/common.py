from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import HybridAStarPlanner
from planner.heuristics import YawFieldHeuristic, compose_guidance
from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx23.common import class_key
from rs_cx27.common import CX27WatchdogConfig, watchdog_evidence
from rs_cx34 import cx34_a_msr as cx34_mod
from rs_cx34.common import CX34SliceSpec, scene_match
from rs_cx35.common import (
    TypedMacroFamily,
    best_macro_score_for_family,
    build_frozen_haa_stack,
    choose_typed_family,
    compile_typed_macro_support,
    reverse_pair_families,
    witness_feature_vector,
)
from rs_cx8.common import primitive_index_from_case, simulate_primitive_detailed


@dataclass(frozen=True)
class TriggerContract:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    margin_floor: float
    high_margin_floor: float
    positive_hits: int
    negative_hits: int


@dataclass(frozen=True)
class EventTriggerContract:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    margin_floor: float
    positive_hits: int
    negative_hits: int


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


def best_primitive_score(case: dict[str, Any], state: tuple[float, float, float], h_pair) -> float:
    pindex = primitive_index_from_case(case)
    max_steer = float(np.deg2rad(float(case['vehicle'].max_steer_deg)))
    cur_anchor, _ = h_pair(float(state[0]), float(state[1]), float(state[2]))
    best = float('-inf')
    for primitive_index in range(len(pindex)):
        steer = float(pindex.actual_steer(int(primitive_index), max_steer))
        direction = int(pindex.actual_direction(int(primitive_index)))
        sim = simulate_primitive_detailed(case, state, steer, direction)
        if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
            continue
        nxt = tuple(float(v) for v in sim['next_state'])
        next_anchor, _ = h_pair(float(nxt[0]), float(nxt[1]), float(nxt[2]))
        best = max(best, float(cur_anchor - next_anchor))
    return float(best)


def _trigger_feature(case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any], margin: float) -> np.ndarray:
    base = witness_feature_vector(case, bundle, ctx, {})
    extra = np.asarray([float(margin)], dtype=np.float32)
    return np.concatenate([base.astype(np.float32), extra], axis=0).astype(np.float32)


def compile_trigger_contract(
    calib_train_assets: list[dict[str, Any]],
    params_obj,
    teacher,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    macro_spec: CX34SliceSpec,
    out_dir: Path,
) -> TriggerContract:
    pos_feats: list[np.ndarray] = []
    pos_margins: list[float] = []
    neg_feats: list[np.ndarray] = []
    neg_margins: list[float] = []
    raw_margins: list[float] = []

    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = cx34_mod.make_policy({'haa_teacher': teacher}, params_obj, case, bundle, field, 'cpu', ablation={'disable_macro_rescue': True})
        planner, h_pair = build_local_proxy(case, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        if hasattr(policy, 'start_search'):
            policy.start_search(planner, tuple(map(float, case['start'])), tuple(map(float, case['goal'])), h_pair, search_state)
        for state in path[:-1]:
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=0.0)
            ctx = policy.prepare_expand(planner, rec, tuple(map(float, case['goal'])), None, None, None, search_state, h_pair)
            if not isinstance(ctx, dict):
                continue
            if str(class_key(ctx)) != 'uncertain|none':
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            if not scene_match(bundle, macro_spec):
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            search_state['last_record_x'] = float(rec.x)
            search_state['last_record_y'] = float(rec.y)
            search_state['last_record_yaw'] = float(rec.yaw)
            family_name, macros, _ = choose_typed_family(case, bundle, ctx, search_state, h_pair, typed_families, typed_support)
            if not macros:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            primitive_best = best_primitive_score(case, (float(rec.x), float(rec.y), float(rec.yaw)), h_pair)
            macro_scores = []
            for family in typed_families:
                if family.name == family_name:
                    score, _ = best_macro_score_for_family(case, (float(rec.x), float(rec.y), float(rec.yaw)), h_pair, family)
                    if np.isfinite(score):
                        macro_scores.append(float(score))
            if not macro_scores:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            margin = float(max(macro_scores) - primitive_best)
            raw_margins.append(margin)
            feat = _trigger_feature(case, bundle, ctx, margin)
            if margin > 0.0:
                pos_feats.append(feat)
                pos_margins.append(margin)
            else:
                neg_feats.append(feat)
                neg_margins.append(margin)
            if hasattr(policy, 'complete_expand'):
                policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)

    pos_band = fit_support_band(pos_feats, pos_margins, low_q=0.05, high_q=0.95, sim_q=0.15) if pos_feats else None
    neg_band = fit_support_band(neg_feats, neg_margins, low_q=0.05, high_q=0.95, sim_q=0.15) if neg_feats else None
    margin_floor = float(np.quantile(np.asarray(pos_margins, dtype=np.float32), 0.20)) if pos_margins else 0.0
    high_margin_floor = float(np.quantile(np.asarray(pos_margins, dtype=np.float32), 0.60)) if pos_margins else 0.0

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'trigger_contract_meta.json').write_text(
        json.dumps(
            {
                'positive_hits': int(len(pos_feats)),
                'negative_hits': int(len(neg_feats)),
                'margin_floor': float(margin_floor),
                'high_margin_floor': float(high_margin_floor),
                'raw_margin_mean': float(np.mean(raw_margins)) if raw_margins else 0.0,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return TriggerContract(
        positive_support=pos_band,
        negative_support=neg_band,
        margin_floor=float(margin_floor),
        high_margin_floor=float(high_margin_floor),
        positive_hits=int(len(pos_feats)),
        negative_hits=int(len(neg_feats)),
    )


def trigger_decision(
    case: dict[str, Any],
    bundle: dict[str, Any],
    ctx: dict[str, Any],
    search_state: dict[str, Any],
    record,
    h_pair,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    trigger_contract: TriggerContract,
    macro_spec: CX34SliceSpec,
    watchdog_cfg: CX27WatchdogConfig,
) -> tuple[bool, list[Any], dict[str, Any]]:
    family_name, macros, _ = choose_typed_family(case, bundle, ctx, search_state, h_pair, typed_families, typed_support)
    if family_name is None or not macros:
        return False, [], {'reason': 'no_family'}
    primitive_best = best_primitive_score(case, (float(record.x), float(record.y), float(record.yaw)), h_pair)
    macro_scores = []
    for family in typed_families:
        if family.name == family_name:
            score, _ = best_macro_score_for_family(case, (float(record.x), float(record.y), float(record.yaw)), h_pair, family)
            if np.isfinite(score):
                macro_scores.append(float(score))
    if not macro_scores:
        return False, [], {'reason': 'no_macro_score'}
    margin = float(max(macro_scores) - primitive_best)
    feat = _trigger_feature(case, bundle, ctx, margin)
    pos_match, pos_sim = support_match(trigger_contract.positive_support, feat, margin, slack=0.0)
    neg_match, neg_sim = support_match(trigger_contract.negative_support, feat, margin, slack=0.0)
    evidence = watchdog_evidence(search_state, record, case, bundle, ctx, watchdog_cfg)
    event_gate = bool(
        bool(evidence.get('blocklist_hit', False))
        or int(evidence.get('recent_failures', 0)) > 0
        or int(evidence.get('stall_steps', 0)) >= 2
        or float(evidence.get('class_churn', 0.0)) >= 0.25
    )
    in_slice = bool(scene_match(bundle, macro_spec))
    allow = False
    reason = 'rejected'
    if in_slice and pos_match and not neg_match and margin >= float(trigger_contract.margin_floor):
        allow = True
        reason = 'slice_pos_support'
    elif in_slice and margin >= float(trigger_contract.high_margin_floor):
        allow = True
        reason = 'slice_high_margin'
    elif (not in_slice) and event_gate and pos_match and not neg_match and margin >= float(trigger_contract.high_margin_floor):
        allow = True
        reason = 'event_pos_support'
    return allow, macros if allow else [], {
        'family_name': family_name,
        'margin': float(margin),
        'primitive_best': float(primitive_best),
        'macro_best': float(max(macro_scores)),
        'pos_match': bool(pos_match),
        'neg_match': bool(neg_match),
        'pos_sim': float(pos_sim),
        'neg_sim': float(neg_sim),
        'event_gate': bool(event_gate),
        'in_slice': bool(in_slice),
        'reason': reason,
    }


def _event_gate_from_evidence(evidence: dict[str, Any]) -> bool:
    return bool(
        bool(evidence.get('blocklist_hit', False))
        or int(evidence.get('recent_failures', 0)) > 0
        or int(evidence.get('stall_steps', 0)) >= 2
        or float(evidence.get('class_churn', 0.0)) >= 0.25
        or float(evidence.get('loop_rate', 0.0)) >= 0.10
    )


def _event_trigger_feature(case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any], evidence: dict[str, Any], margin: float) -> np.ndarray:
    base = witness_feature_vector(case, bundle, ctx, {})
    extra = np.asarray(
        [
            float(margin),
            float(evidence.get('stall_steps', 0)),
            float(evidence.get('class_churn', 0.0)),
            float(evidence.get('loop_rate', 0.0)),
            float(evidence.get('recent_failures', 0)),
            float(1.0 if bool(evidence.get('blocklist_hit', False)) else 0.0),
        ],
        dtype=np.float32,
    )
    return np.concatenate([base.astype(np.float32), extra], axis=0).astype(np.float32)


def compile_event_trigger_contract(
    calib_train_assets: list[dict[str, Any]],
    parent_policy_factory,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    macro_spec: CX34SliceSpec,
    watchdog_cfg: CX27WatchdogConfig,
    out_dir: Path,
) -> EventTriggerContract:
    pos_feats: list[np.ndarray] = []
    pos_margins: list[float] = []
    neg_feats: list[np.ndarray] = []
    neg_margins: list[float] = []

    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = parent_policy_factory(case, bundle, field)
        planner, h_pair = build_local_proxy(case, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        if hasattr(policy, 'start_search'):
            policy.start_search(planner, tuple(map(float, case['start'])), tuple(map(float, case['goal'])), h_pair, search_state)
        for state in path[:-1]:
            anchor, _ = h_pair(float(state[0]), float(state[1]), float(state[2]))
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=float(anchor))
            ctx = policy.prepare_expand(planner, rec, tuple(map(float, case['goal'])), None, None, None, search_state, h_pair)
            if not isinstance(ctx, dict):
                continue
            if str(class_key(ctx)) != 'uncertain|none':
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            if scene_match(bundle, macro_spec):
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            evidence = watchdog_evidence(search_state, rec, case, bundle, ctx, watchdog_cfg)
            if not _event_gate_from_evidence(evidence):
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            search_state['last_record_x'] = float(rec.x)
            search_state['last_record_y'] = float(rec.y)
            search_state['last_record_yaw'] = float(rec.yaw)
            family_name, macros, _ = choose_typed_family(case, bundle, ctx, search_state, h_pair, typed_families, typed_support)
            if not macros or family_name is None:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            primitive_best = best_primitive_score(case, (float(rec.x), float(rec.y), float(rec.yaw)), h_pair)
            macro_scores = []
            for family in typed_families:
                if family.name == family_name:
                    score, _ = best_macro_score_for_family(case, (float(rec.x), float(rec.y), float(rec.yaw)), h_pair, family)
                    if np.isfinite(score):
                        macro_scores.append(float(score))
            if not macro_scores:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            margin = float(max(macro_scores) - primitive_best)
            feat = _event_trigger_feature(case, bundle, ctx, evidence, margin)
            if margin > 0.0:
                pos_feats.append(feat)
                pos_margins.append(margin)
            else:
                neg_feats.append(feat)
                neg_margins.append(margin)
            if hasattr(policy, 'complete_expand'):
                policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)

    pos_band = fit_support_band(pos_feats, pos_margins, low_q=0.05, high_q=0.95, sim_q=0.15) if pos_feats else None
    neg_band = fit_support_band(neg_feats, neg_margins, low_q=0.05, high_q=0.95, sim_q=0.15) if neg_feats else None
    margin_floor = float(np.quantile(np.asarray(pos_margins, dtype=np.float32), 0.20)) if pos_margins else 0.0
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'event_trigger_meta.json').write_text(
        json.dumps(
            {
                'positive_hits': int(len(pos_feats)),
                'negative_hits': int(len(neg_feats)),
                'margin_floor': float(margin_floor),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return EventTriggerContract(
        positive_support=pos_band,
        negative_support=neg_band,
        margin_floor=float(margin_floor),
        positive_hits=int(len(pos_feats)),
        negative_hits=int(len(neg_feats)),
    )


def event_trigger_decision(
    case: dict[str, Any],
    bundle: dict[str, Any],
    ctx: dict[str, Any],
    search_state: dict[str, Any],
    record,
    h_pair,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    event_contract: EventTriggerContract,
    macro_spec: CX34SliceSpec,
    watchdog_cfg: CX27WatchdogConfig,
) -> tuple[bool, list[Any], dict[str, Any]]:
    if scene_match(bundle, macro_spec):
        return False, [], {'reason': 'in_slice'}
    evidence = watchdog_evidence(search_state, record, case, bundle, ctx, watchdog_cfg)
    if not _event_gate_from_evidence(evidence):
        return False, [], {'reason': 'no_event'}
    family_name, macros, _ = choose_typed_family(case, bundle, ctx, search_state, h_pair, typed_families, typed_support)
    if family_name is None or not macros:
        return False, [], {'reason': 'no_family'}
    primitive_best = best_primitive_score(case, (float(record.x), float(record.y), float(record.yaw)), h_pair)
    macro_scores = []
    for family in typed_families:
        if family.name == family_name:
            score, _ = best_macro_score_for_family(case, (float(record.x), float(record.y), float(record.yaw)), h_pair, family)
            if np.isfinite(score):
                macro_scores.append(float(score))
    if not macro_scores:
        return False, [], {'reason': 'no_macro_score'}
    margin = float(max(macro_scores) - primitive_best)
    feat = _event_trigger_feature(case, bundle, ctx, evidence, margin)
    pos_match, pos_sim = support_match(event_contract.positive_support, feat, margin, slack=0.0)
    neg_match, neg_sim = support_match(event_contract.negative_support, feat, margin, slack=0.0)
    allow = bool(pos_match and not neg_match and margin >= float(event_contract.margin_floor))
    return allow, macros if allow else [], {
        'family_name': family_name,
        'margin': float(margin),
        'pos_match': bool(pos_match),
        'neg_match': bool(neg_match),
        'pos_sim': float(pos_sim),
        'neg_sim': float(neg_sim),
        'event_gate': True,
    }


__all__ = [
    'CX27WatchdogConfig',
    'CX34SliceSpec',
    'EventTriggerContract',
    'TriggerContract',
    'best_primitive_score',
    'build_frozen_haa_stack',
    'build_local_proxy',
    'compile_event_trigger_contract',
    'compile_trigger_contract',
    'event_trigger_decision',
    'trigger_decision',
]
