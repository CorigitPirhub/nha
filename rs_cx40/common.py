from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorCandidate
from rs_cx23.common import class_key
from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx27.common import coarse_state_key, scene_kind, watchdog_evidence
from rs_cx36.common import build_local_proxy
from rs_cx39.common import BridgePathCandidate, enumerate_bridge_paths


@dataclass(frozen=True)
class BridgePrescreener:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    score_floor: float
    depth2_floor: float
    positive_hits: int
    negative_hits: int


@dataclass(frozen=True)
class MemoizedWitness:
    active: bool
    macro_primitive_indices: tuple[int, ...]
    prior_score: float
    feature_proto: np.ndarray
    hits: int


@dataclass(frozen=True)
class SeedBankEntry:
    active: bool
    macro_primitive_indices: tuple[int, ...]
    prior_score: float
    feature_proto: np.ndarray
    hits: int


def event_scheduler_score(ctx: dict[str, Any], evidence: dict[str, Any]) -> float:
    from rs_cx39.cx39_b_cbs import _event_score

    return float(max(_event_score(evidence), 0.4 if str(class_key(ctx)) == 'uncertain|none' else 0.0))


def primitive_candidates_from_record(case: dict[str, Any], planner, record, h_pair) -> list[SuccessorCandidate]:
    raw: list[SuccessorCandidate] = []
    prev_steer = float(getattr(record, 'steer', 0.0))
    for primitive_index, (steer, direction) in enumerate(planner.motion_primitives):
        sim = planner._simulate_detailed(float(record.x), float(record.y), float(record.yaw), float(steer), int(direction))
        if not sim or not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
            continue
        nx, ny, nyaw = sim['next_state']
        edge = float(planner._edge_cost(planner.cfg.step_size, float(steer), float(prev_steer), int(direction)))
        na, nguided = h_pair(float(nx), float(ny), float(nyaw))
        raw.append(
            SuccessorCandidate(
                primitive_index=int(primitive_index),
                steer=float(steer),
                direction=int(direction),
                next_state=(float(nx), float(ny), float(nyaw)),
                edge_cost=float(edge),
                anchor=float(na),
                guided=float(nguided),
                sim_info=sim,
                family=None,
                source='primitive',
                segment_states=((float(nx), float(ny), float(nyaw)),),
            )
        )
    return raw


def bridge_efficiency(case: dict[str, Any], h_pair, current_anchor: float, bridge: BridgePathCandidate) -> float:
    from rs_cx38.common import bounded_local_review_score

    cand = SuccessorCandidate(
        primitive_index=-1,
        steer=float(bridge.first_steer),
        direction=int(bridge.direction),
        next_state=tuple(bridge.next_state),
        edge_cost=float(bridge.edge_cost),
        anchor=float(bridge.anchor),
        guided=float(bridge.guided),
        sim_info={'bridge_primitives': tuple(int(v) for v in bridge.primitive_indices)},
        family='bridge_only',
        source='bridge_only',
        segment_states=tuple(bridge.segment_states),
    )
    raw = float(bounded_local_review_score(case, h_pair, float(current_anchor), cand))
    return float(raw / max(float(cand.edge_cost), 1e-6))


def review_efficiency_for_candidate(case: dict[str, Any], h_pair, current_anchor: float, cand: SuccessorCandidate) -> float:
    from rs_cx38.common import bounded_local_review_score

    raw = float(bounded_local_review_score(case, h_pair, float(current_anchor), cand))
    return float(raw / max(float(getattr(cand, 'edge_cost', 0.0)), 1e-6))


def runtime_bridge_feature(evidence: dict[str, Any], current_anchor: float, bridge: BridgePathCandidate, *, bridge_eff: float, scheduler_score: float) -> np.ndarray:
    kind = str(evidence.get('scene_kind', 'default'))
    return np.asarray(
        [
            float(1.0 if kind == 'default' else 0.0),
            float(1.0 if kind == 'maze' else 0.0),
            float(1.0 if kind == 'misc' else 0.0),
            float(scheduler_score),
            float(evidence.get('stall_steps', 0)),
            float(evidence.get('class_churn', 0.0)),
            float(evidence.get('loop_rate', 0.0)),
            float(evidence.get('recent_failures', 0)),
            float(1.0 if bool(evidence.get('blocklist_hit', False)) else 0.0),
            float(len(bridge.primitive_indices)),
            float(current_anchor - float(bridge.anchor)),
            float(current_anchor - float(bridge.guided)),
            float(bridge.edge_cost),
            float(bridge_eff),
        ],
        dtype=np.float32,
    )


def _bucket(value: float, scale: float, lo: int = -32, hi: int = 32) -> int:
    if scale <= 0.0:
        return 0
    return int(np.clip(np.floor(float(value) / float(scale)), int(lo), int(hi)))


def witness_cache_signature(
    case: dict[str, Any],
    bundle: dict[str, Any],
    node_ctx: dict[str, Any],
    evidence: dict[str, Any],
    bridge: BridgePathCandidate,
    *,
    cell_stride: int,
    yaw_bins: int,
    scheduler_score: float,
    bridge_eff: float,
) -> tuple[Any, ...]:
    end_rec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]))
    coarse = coarse_state_key(end_rec, case, cell_stride=int(cell_stride), yaw_bins=int(yaw_bins))
    prefix = tuple(int(v) for v in bridge.primitive_indices)
    return (
        str(scene_kind(case, bundle)),
        str(class_key(node_ctx)),
        int(coarse[0]),
        int(coarse[1]),
        int(coarse[2]),
        tuple(int(v) for v in prefix),
        _bucket(float(scheduler_score), 0.2),
        int(min(int(evidence.get('stall_steps', 0)), 4)),
        int(min(int(evidence.get('recent_failures', 0)), 3)),
        int(bool(evidence.get('blocklist_hit', False))),
        _bucket(float(bridge_eff), 0.25),
    )


def seed_bank_signature(
    case: dict[str, Any],
    bundle: dict[str, Any],
    node_ctx: dict[str, Any],
    evidence: dict[str, Any],
    bridge: BridgePathCandidate,
    *,
    cell_stride: int,
    yaw_bins: int,
    scheduler_score: float,
) -> tuple[Any, ...]:
    end_rec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]))
    coarse = coarse_state_key(end_rec, case, cell_stride=max(int(cell_stride) * 2, 1), yaw_bins=max(int(yaw_bins) // 2, 1))
    return (
        str(scene_kind(case, bundle)),
        str(class_key(node_ctx)),
        int(coarse[0]),
        int(coarse[1]),
        int(coarse[2]),
        int(len(bridge.primitive_indices)),
        _bucket(float(scheduler_score), 0.4),
        int(min(int(evidence.get('stall_steps', 0)), 4)),
        int(min(int(evidence.get('recent_failures', 0)), 3)),
        int(bool(evidence.get('blocklist_hit', False))),
    )


def reconstruct_macro_from_indices(typed_families: tuple[Any, ...], primitive_indices: tuple[int, ...]) -> Any | None:
    target = tuple(int(v) for v in primitive_indices)
    for family in typed_families:
        for macro in getattr(family, 'macros', ()):
            if tuple(int(v) for v in getattr(macro, 'primitive_indices', ())) == target:
                return macro
    return None


def cache_feature_consistent(entry: MemoizedWitness, feat: np.ndarray, *, tol_mean: float = 0.12, tol_max: float = 0.35) -> bool:
    proto = np.asarray(entry.feature_proto, dtype=np.float32)
    cur = np.asarray(feat, dtype=np.float32)
    if proto.shape != cur.shape:
        return False
    diff = np.abs(proto - cur)
    return bool(float(np.mean(diff)) <= float(tol_mean) and float(np.max(diff)) <= float(tol_max))


def prescreener_decision(contract: BridgePrescreener | None, feat: np.ndarray, score_hint: float) -> tuple[bool, bool, float]:
    if contract is None:
        return True, False, 1.0
    pos_match, pos_sim = support_match(contract.positive_support, feat, float(score_hint), slack=0.0)
    neg_match, neg_sim = support_match(contract.negative_support, feat, float(score_hint), slack=0.0)
    score = float(max(pos_sim, 0.0) - max(neg_sim, 0.0))
    allow = bool((pos_match or float(score_hint) >= float(contract.score_floor)) and not neg_match)
    escalate = bool((pos_match or float(score_hint) >= float(contract.depth2_floor)) and score > 0.0)
    return allow, escalate, score


def compile_bridge_prescreener(
    calib_train_assets: list[dict[str, Any]],
    *,
    memory: dict[str, Any],
    params_obj,
) -> BridgePrescreener:
    from rs_cx39 import cx39_b_cbs as bridge_mod
    from rs_cx39 import cx39_c_cbc as contract_mod

    pos_feats: list[np.ndarray] = []
    pos_scores: list[float] = []
    neg_feats: list[np.ndarray] = []
    neg_scores: list[float] = []

    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        field = np.asarray(asset['field'], dtype=np.float32)
        planner, h_pair = build_local_proxy(case, field)
        policy = contract_mod.make_policy(memory, params_obj, case, bundle, field, 'cpu', ablation=None)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        if hasattr(policy, 'start_search'):
            policy.start_search(planner, tuple(map(float, case['start'])), tuple(map(float, case['goal'])), h_pair, search_state)
        for state in path[:-1]:
            anchor, _ = h_pair(float(state[0]), float(state[1]), float(state[2]))
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=float(anchor), steer=0.0)
            ctx = policy.prepare_expand(planner, rec, tuple(map(float, case['goal'])), None, None, None, search_state, h_pair)
            if not isinstance(ctx, dict):
                continue
            evidence = watchdog_evidence(search_state, rec, case, bundle, ctx, policy.watchdog_cfg)
            scheduler_score = max(event_scheduler_score(ctx, evidence), 0.0)
            if scheduler_score <= 0.0:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            primitive_cands = primitive_candidates_from_record(case, planner, rec, h_pair)
            if not primitive_cands:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            current_anchor = float(anchor)
            primitive_floor = max(review_efficiency_for_candidate(case, h_pair, float(current_anchor), cand) for cand in primitive_cands)
            bridge_paths = enumerate_bridge_paths(
                case,
                planner,
                h_pair,
                primitive_cands,
                max_depth=int(max(getattr(params_obj, 'max_bridge_depth', 1), 1)),
                max_frontier=int(max(getattr(params_obj, 'max_bridge_frontier', 1), 1)),
            )
            if not bridge_paths:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            bridge_floor = max(bridge_efficiency(case, h_pair, float(current_anchor), bridge) for bridge in bridge_paths)
            counterfactual_floor = float(max(primitive_floor, bridge_floor))

            for bridge in bridge_paths:
                eff = bridge_efficiency(case, h_pair, float(current_anchor), bridge)
                feat = runtime_bridge_feature(evidence, float(current_anchor), bridge, bridge_eff=float(eff), scheduler_score=float(scheduler_score))
                srec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]), anchor=float(bridge.anchor))
                tmp_search = dict(search_state)
                tmp_search['last_record_x'] = float(srec.x)
                tmp_search['last_record_y'] = float(srec.y)
                tmp_search['last_record_yaw'] = float(srec.yaw)
                sctx = policy.base.prepare_expand(planner, srec, tuple(map(float, case['goal'])), None, None, None, tmp_search, h_pair)
                if not isinstance(sctx, dict):
                    neg_feats.append(feat)
                    neg_scores.append(float(scheduler_score))
                    continue
                active, macros, info = bridge_mod.compatibility_bridge_prior(
                    case,
                    bundle,
                    sctx,
                    tmp_search,
                    srec,
                    h_pair,
                    typed_families=policy.typed_macro_families,
                    typed_support=policy.typed_macro_support,
                    replay_contract=policy.replay_contract,
                    macro_spec=policy.macro_spec,
                    watchdog_cfg=policy.watchdog_cfg,
                )
                label = False
                if active and macros:
                    review_rows = contract_mod.bridge_review_candidates(case, planner, h_pair, [(bridge, macros[0], float(info.get('compatibility_score', 0.0)), float(max(current_anchor - float(bridge.anchor), 0.0) + 0.35 * max(current_anchor - float(bridge.guided), 0.0)))], source='bridge_review')
                    if review_rows:
                        final_eff = review_efficiency_for_candidate(case, h_pair, float(current_anchor), review_rows[0])
                        label = bool(float(final_eff) > float(counterfactual_floor))
                if label:
                    pos_feats.append(feat)
                    pos_scores.append(float(scheduler_score))
                else:
                    neg_feats.append(feat)
                    neg_scores.append(float(scheduler_score))
            if hasattr(policy, 'complete_expand'):
                policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)

    pos_band = fit_support_band(pos_feats, pos_scores, low_q=0.05, high_q=0.95, sim_q=0.15) if pos_feats else None
    neg_band = fit_support_band(neg_feats, neg_scores, low_q=0.05, high_q=0.95, sim_q=0.15) if neg_feats else None
    score_floor = float(np.quantile(np.asarray(pos_scores, dtype=np.float32), 0.05)) if pos_scores else 0.0
    depth2_floor = float(np.quantile(np.asarray(pos_scores, dtype=np.float32), 0.60)) if pos_scores else 1.0
    return BridgePrescreener(
        positive_support=pos_band,
        negative_support=neg_band,
        score_floor=float(score_floor),
        depth2_floor=float(depth2_floor),
        positive_hits=int(len(pos_feats)),
        negative_hits=int(len(neg_feats)),
    )


__all__ = [
    'BridgePrescreener',
    'MemoizedWitness',
    'SeedBankEntry',
    'bridge_efficiency',
    'cache_feature_consistent',
    'compile_bridge_prescreener',
    'event_scheduler_score',
    'prescreener_decision',
    'primitive_candidates_from_record',
    'reconstruct_macro_from_indices',
    'review_efficiency_for_candidate',
    'runtime_bridge_feature',
    'seed_bank_signature',
    'witness_cache_signature',
]
