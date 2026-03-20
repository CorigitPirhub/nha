from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx27.common import CX27WatchdogConfig, watchdog_evidence
from rs_cx34.common import CX34SliceSpec, scene_match
from rs_cx35.common import (
    TypedMacroFamily,
    best_macro_score_for_family,
    build_frozen_haa_stack,
    choose_typed_family,
    witness_feature_vector,
)
from rs_cx36.common import best_primitive_score, build_local_proxy
from rs_cx8.common import primitive_index_from_case, simulate_primitive_detailed


@dataclass(frozen=True)
class ReplayTriggerContract:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    margin_floor: float
    high_margin_floor: float
    positive_hits: int
    negative_hits: int


def replay_feature(case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any], evidence: dict[str, Any], margin: float, step_clearance: float) -> np.ndarray:
    base = witness_feature_vector(case, bundle, ctx, {})
    extra = np.asarray(
        [
            float(margin),
            float(step_clearance),
            float(evidence.get('stall_steps', 0)),
            float(evidence.get('class_churn', 0.0)),
            float(evidence.get('loop_rate', 0.0)),
            float(evidence.get('recent_failures', 0)),
        ],
        dtype=np.float32,
    )
    return np.concatenate([base.astype(np.float32), extra], axis=0).astype(np.float32)


def compile_replay_trigger_contract(
    calib_train_assets: list[dict[str, Any]],
    parent_policy_factory,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    macro_spec: CX34SliceSpec,
    watchdog_cfg: CX27WatchdogConfig,
    out_dir: Path,
) -> ReplayTriggerContract:
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
        trace = list(asset.get('trace', []))
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        if hasattr(policy, 'start_search'):
            policy.start_search(planner, tuple(map(float, case['start'])), tuple(map(float, case['goal'])), h_pair, search_state)
        pindex = primitive_index_from_case(case)
        max_steer = float(np.deg2rad(float(case['vehicle'].max_steer_deg)))
        for idx, state in enumerate(path[:-1]):
            anchor, _ = h_pair(float(state[0]), float(state[1]), float(state[2]))
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=float(anchor))
            ctx = policy.prepare_expand(planner, rec, tuple(map(float, case['goal'])), None, None, None, search_state, h_pair)
            if not isinstance(ctx, dict):
                continue
            path_prim = int(trace[idx]) if idx < len(trace) else None
            for prim_idx in range(len(pindex)):
                if path_prim is not None and int(prim_idx) == int(path_prim):
                    continue
                steer = float(pindex.actual_steer(int(prim_idx), max_steer))
                direction = int(pindex.actual_direction(int(prim_idx)))
                sim = simulate_primitive_detailed(case, (float(rec.x), float(rec.y), float(rec.yaw)), steer, direction)
                if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
                    continue
                nxt = tuple(float(v) for v in sim['next_state'])
                nanchor, _ = h_pair(float(nxt[0]), float(nxt[1]), float(nxt[2]))
                srec = SimpleNamespace(x=float(nxt[0]), y=float(nxt[1]), yaw=float(nxt[2]), anchor=float(nanchor))
                sctx = policy.prepare_expand(planner, srec, tuple(map(float, case['goal'])), None, None, None, search_state, h_pair)
                if not isinstance(sctx, dict):
                    continue
                if str(case.get('scenario', '')) == 'parasol_misc' and scene_match(bundle, macro_spec):
                    continue
                if str(sctx.get('mode', 'uncertain')) == 'uncertain' and str(sctx.get('rules', {})) == '{}':
                    continue
                evidence = watchdog_evidence(search_state, srec, case, bundle, sctx, watchdog_cfg)
                search_state['last_record_x'] = float(srec.x)
                search_state['last_record_y'] = float(srec.y)
                search_state['last_record_yaw'] = float(srec.yaw)
                family_name, macros, _ = choose_typed_family(case, bundle, sctx, search_state, h_pair, typed_families, typed_support)
                if family_name is None or not macros:
                    continue
                primitive_best = best_primitive_score(case, (float(srec.x), float(srec.y), float(srec.yaw)), h_pair)
                macro_scores = []
                for family in typed_families:
                    if family.name == family_name:
                        score, _ = best_macro_score_for_family(case, (float(srec.x), float(srec.y), float(srec.yaw)), h_pair, family)
                        if np.isfinite(score):
                            macro_scores.append(float(score))
                if not macro_scores:
                    continue
                margin = float(max(macro_scores) - primitive_best)
                feat = replay_feature(case, bundle, sctx, evidence, margin, float(sim.get('min_clearance', 0.0)))
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
    (out_dir / 'replay_trigger_meta.json').write_text(
        json.dumps(
            {
                'positive_hits': int(len(pos_feats)),
                'negative_hits': int(len(neg_feats)),
                'margin_floor': float(margin_floor),
                'high_margin_floor': float(high_margin_floor),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return ReplayTriggerContract(
        positive_support=pos_band,
        negative_support=neg_band,
        margin_floor=float(margin_floor),
        high_margin_floor=float(high_margin_floor),
        positive_hits=int(len(pos_feats)),
        negative_hits=int(len(neg_feats)),
    )


def replay_trigger_decision(
    case: dict[str, Any],
    bundle: dict[str, Any],
    ctx: dict[str, Any],
    search_state: dict[str, Any],
    record,
    h_pair,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    replay_contract: ReplayTriggerContract,
    macro_spec: CX34SliceSpec,
    watchdog_cfg: CX27WatchdogConfig,
) -> tuple[bool, list[Any], dict[str, Any]]:
    if str(case.get('scenario', '')) == 'parasol_misc' and scene_match(bundle, macro_spec):
        return False, [], {'reason': 'in_slice'}
    evidence = watchdog_evidence(search_state, record, case, bundle, ctx, watchdog_cfg)
    if not (
        bool(evidence.get('blocklist_hit', False))
        or int(evidence.get('recent_failures', 0)) > 0
        or int(evidence.get('stall_steps', 0)) >= 2
        or float(evidence.get('class_churn', 0.0)) >= 0.25
        or float(evidence.get('loop_rate', 0.0)) >= 0.10
    ):
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
    feat = replay_feature(case, bundle, ctx, evidence, margin, 0.0)
    pos_match, pos_sim = support_match(replay_contract.positive_support, feat, margin, slack=0.0)
    neg_match, neg_sim = support_match(replay_contract.negative_support, feat, margin, slack=0.0)
    allow = bool(pos_match and not neg_match and margin >= float(replay_contract.margin_floor))
    return allow, macros if allow else [], {
        'family_name': family_name,
        'margin': float(margin),
        'pos_match': bool(pos_match),
        'neg_match': bool(neg_match),
        'pos_sim': float(pos_sim),
        'neg_sim': float(neg_sim),
    }


def replay_priority_prior(
    case: dict[str, Any],
    bundle: dict[str, Any],
    ctx: dict[str, Any],
    search_state: dict[str, Any],
    record,
    h_pair,
    *,
    typed_families: tuple[TypedMacroFamily, ...],
    typed_support: dict[str, Any],
    replay_contract: ReplayTriggerContract,
    macro_spec: CX34SliceSpec,
    watchdog_cfg: CX27WatchdogConfig,
) -> tuple[bool, list[Any], dict[str, Any]]:
    if str(case.get('scenario', '')) == 'parasol_misc' and scene_match(bundle, macro_spec):
        return False, [], {'reason': 'in_slice'}
    evidence = watchdog_evidence(search_state, record, case, bundle, ctx, watchdog_cfg)
    event_score = float(
        0.30 * min(float(evidence.get('stall_steps', 0)) / 4.0, 1.0)
        + 0.25 * min(float(evidence.get('class_churn', 0.0)) / 0.5, 1.0)
        + 0.20 * min(float(evidence.get('loop_rate', 0.0)) / 0.2, 1.0)
        + 0.15 * min(float(evidence.get('recent_failures', 0)) / 2.0, 1.0)
        + 0.10 * float(1.0 if bool(evidence.get('blocklist_hit', False)) else 0.0)
    )
    if event_score <= 0.0:
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
    feat = replay_feature(case, bundle, ctx, evidence, margin, 0.0)
    pos_match, pos_sim = support_match(replay_contract.positive_support, feat, margin, slack=0.0)
    neg_match, neg_sim = support_match(replay_contract.negative_support, feat, margin, slack=0.0)
    margin_score = float(np.clip(margin / max(float(replay_contract.high_margin_floor), 1e-6), 0.0, 2.0))
    prior_score = float(0.45 * margin_score + 0.35 * event_score + 0.20 * float(pos_sim if pos_match else 0.0))
    active = bool((pos_match or margin >= float(replay_contract.margin_floor)) and not neg_match and prior_score > 0.0)
    return active, macros if active else [], {
        'family_name': family_name,
        'margin': float(margin),
        'primitive_best': float(primitive_best),
        'macro_best': float(max(macro_scores)),
        'event_score': float(event_score),
        'margin_score': float(margin_score),
        'prior_score': float(prior_score),
        'pos_match': bool(pos_match),
        'neg_match': bool(neg_match),
        'pos_sim': float(pos_sim),
        'neg_sim': float(neg_sim),
    }


__all__ = [
    'ReplayTriggerContract',
    'build_frozen_haa_stack',
    'compile_replay_trigger_contract',
    'replay_priority_prior',
    'replay_trigger_decision',
]
