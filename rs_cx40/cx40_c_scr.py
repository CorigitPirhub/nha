from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorDecision
from rs_cx.common import CXGlobalConfig
from rs_cx38.common import review_priority_delta
from rs_cx39 import cx39_b_cbs as bridge_mod
from rs_cx39.common import BridgePathCandidate, bridge_review_candidates, enumerate_bridge_paths
from rs_cx40 import cx40_a_cas as parent_mod
from rs_cx40.common import (
    MemoizedWitness,
    bridge_efficiency,
    cache_feature_consistent,
    event_scheduler_score,
    prescreener_decision,
    reconstruct_macro_from_indices,
    review_efficiency_for_candidate,
    runtime_bridge_feature,
    witness_cache_signature,
)
from rs_cx36.common import build_local_proxy


@dataclass(frozen=True)
class CX40CSCRParams:
    turn_bridge_max: float
    turn_focus_max: float
    rescue_bridge_max: float
    rescue_focus_min: float
    rescue_path_min: float
    rescue_budget: int
    suppress_bridge_min: float
    suppress_bridge_max: float
    suppress_focus_max: float
    suppress_path_min: float
    stubborn_bridge_min: float
    stubborn_focus_max: float
    stubborn_path_max: float
    macro_bridge_min: float
    macro_bridge_max: float
    macro_focus_min: float
    macro_focus_max: float
    macro_path_min: float
    macro_path_max: float
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int
    min_hits: int
    max_bridge_depth: int
    max_bridge_frontier: int
    max_review_targets: int
    max_screened_paths: int
    seed_min_hits: int


def param_grid() -> list[CX40CSCRParams]:
    return [
        CX40CSCRParams(**dict(params.__dict__, seed_min_hits=2))
        for params in parent_mod.param_grid()
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Seed-Cache', 'disable_seed_cache': True},
        {'name': 'No-Online-Refinement', 'disable_online_refinement': True},
    ]


def _bridge_review_score(current_anchor: float, bridge: BridgePathCandidate) -> float:
    return float(max(float(current_anchor) - float(bridge.anchor), 0.0) + 0.35 * max(float(current_anchor) - float(bridge.guided), 0.0))


def _compile_seed_cache(calib_train_assets: list[dict[str, Any]], *, memory: dict[str, Any], params_obj: CX40CSCRParams) -> dict[tuple[Any, ...], MemoizedWitness]:
    seed_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    driver_params = parent_mod.CX40ACASParams(**{k: v for k, v in params_obj.__dict__.items() if k != 'seed_min_hits'})
    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = parent_mod.CASPolicy(case, bundle, field, driver_params, memory, disable_prescreener=False, disable_depth2_escalation=False)
        planner, h_pair = build_local_proxy(case, field)
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
            evidence = bridge_mod.watchdog_evidence(search_state, rec, case, bundle, ctx, policy.watchdog_cfg)
            scheduler_score = event_scheduler_score(ctx, evidence)
            if scheduler_score <= 0.0:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            primitive_cands = [cand for cand in parent_mod.primitive_candidates_from_record(case, planner, rec, h_pair) if str(getattr(cand, 'source', 'primitive')) == 'primitive']
            if not primitive_cands:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            current_anchor = float(anchor)
            depth1_paths = enumerate_bridge_paths(case, planner, h_pair, primitive_cands, max_depth=1, max_frontier=int(max(params_obj.max_bridge_frontier, 1)))
            if not depth1_paths:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)
                continue
            for bridge in depth1_paths:
                bridge_eff = bridge_efficiency(case, h_pair, float(current_anchor), bridge)
                feat = runtime_bridge_feature(evidence, float(current_anchor), bridge, bridge_eff=float(bridge_eff), scheduler_score=float(scheduler_score))
                allow, escalate, _ = prescreener_decision(policy.prescreener, feat, float(scheduler_score))
                if not allow:
                    continue
                sig = witness_cache_signature(
                    case,
                    bundle,
                    ctx,
                    evidence,
                    bridge,
                    cell_stride=int(policy.watchdog_cfg.cell_stride),
                    yaw_bins=int(policy.watchdog_cfg.yaw_bins),
                    scheduler_score=float(scheduler_score),
                    bridge_eff=float(bridge_eff),
                )
                bucket = seed_rows.setdefault(sig, {'count': 0, 'active': 0, 'inactive': 0, 'feat_sum': np.zeros_like(feat, dtype=np.float32), 'macro_counts': {}, 'prior_sum': 0.0})
                bucket['count'] += 1
                bucket['feat_sum'] = np.asarray(bucket['feat_sum'], dtype=np.float32) + np.asarray(feat, dtype=np.float32)
                srec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]), anchor=float(bridge.anchor))
                tmp_search = dict(search_state)
                tmp_search['last_record_x'] = float(srec.x)
                tmp_search['last_record_y'] = float(srec.y)
                tmp_search['last_record_yaw'] = float(srec.yaw)
                sctx = policy.base.prepare_expand(planner, srec, tuple(map(float, case['goal'])), None, None, None, tmp_search, h_pair)
                active = False
                macro_indices: tuple[int, ...] = ()
                prior = 0.0
                if isinstance(sctx, dict):
                    allow2, macros, info = bridge_mod.compatibility_bridge_prior(
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
                    if allow2 and macros:
                        active = True
                        macro_indices = tuple(int(v) for v in getattr(macros[0], 'primitive_indices', ()))
                        prior = float(info.get('compatibility_score', 0.0))
                if active:
                    bucket['active'] += 1
                    bucket['prior_sum'] += float(prior)
                    bucket['macro_counts'][macro_indices] = int(bucket['macro_counts'].get(macro_indices, 0)) + 1
                else:
                    bucket['inactive'] += 1
            if hasattr(policy, 'complete_expand'):
                policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, ctx, 0, 0, 0, search_state, h_pair)

    out: dict[tuple[Any, ...], MemoizedWitness] = {}
    for sig, bucket in seed_rows.items():
        count = int(bucket['count'])
        if count < int(max(params_obj.seed_min_hits, 1)):
            continue
        feat_proto = np.asarray(bucket['feat_sum'], dtype=np.float32) / float(max(count, 1))
        active = int(bucket['active'])
        inactive = int(bucket['inactive'])
        if active > 0 and inactive == 0:
            macro_counts = dict(bucket['macro_counts'])
            macro_indices = max(macro_counts.items(), key=lambda item: int(item[1]))[0] if macro_counts else tuple()
            out[sig] = MemoizedWitness(True, tuple(int(v) for v in macro_indices), float(bucket['prior_sum']) / float(max(active, 1)), feat_proto, count)
        elif inactive > 0 and active == 0:
            out[sig] = MemoizedWitness(False, tuple(), 0.0, feat_proto, count)
    return out


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX40CSCRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k != 'seed_min_hits'})
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    seed_cache = _compile_seed_cache(calib_train_assets, memory=memory, params_obj=params)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx40_c_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'seed_cache_size': int(len(seed_cache)),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    memory = dict(memory)
    memory['seed_witness_cache'] = seed_cache
    return memory


class SCRPolicy:
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX40CSCRParams,
        memory: dict[str, Any],
        *,
        disable_seed_cache: bool = False,
        disable_online_refinement: bool = False,
    ) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_seed_cache = bool(disable_seed_cache)
        self.disable_online_refinement = bool(disable_online_refinement)
        parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k != 'seed_min_hits'})
        driver = parent_mod.CASPolicy(case, bundle, field, parent_params, memory, disable_prescreener=False, disable_depth2_escalation=False)
        self.base = driver.base
        self.typed_macro_families = tuple(driver.typed_macro_families)
        self.typed_macro_support = dict(driver.typed_macro_support)
        self.replay_contract = driver.replay_contract
        self.macro_spec = driver.macro_spec
        self.watchdog_cfg = driver.watchdog_cfg
        self.prescreener = driver.prescreener
        self.seed_cache: dict[tuple[Any, ...], MemoizedWitness] = {} if self.disable_seed_cache else dict(memory.get('seed_witness_cache', {}))
        self.online_cache: dict[tuple[Any, ...], MemoizedWitness] = {}
        self.stats: dict[str, float] = {
            'scheduler_hits': 0.0,
            'depth1_paths': 0.0,
            'screened_paths': 0.0,
            'depth2_escalations': 0.0,
            'depth2_paths': 0.0,
            'expensive_bridge_evals': 0.0,
            'contract_pass': 0.0,
            'contract_reject': 0.0,
            'seed_hits': 0.0,
            'online_hits': 0.0,
            'cache_misses': 0.0,
        }

    def start_search(self, planner, start, goal, h_pair, search_state):
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        search_state['last_record_x'] = float(record.x)
        search_state['last_record_y'] = float(record.y)
        search_state['last_record_yaw'] = float(record.yaw)
        return self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def _cache_lookup(self, sig: tuple[Any, ...], feat: np.ndarray) -> tuple[str | None, MemoizedWitness | None]:
        entry = self.online_cache.get(sig)
        if entry is not None and cache_feature_consistent(entry, feat):
            self.stats['online_hits'] = float(self.stats.get('online_hits', 0.0) + 1.0)
            return 'online', entry
        entry = self.seed_cache.get(sig)
        if entry is not None and cache_feature_consistent(entry, feat):
            self.stats['seed_hits'] = float(self.stats.get('seed_hits', 0.0) + 1.0)
            return 'seed', entry
        self.stats['cache_misses'] = float(self.stats.get('cache_misses', 0.0) + 1.0)
        return None, None

    def _update_online_cache(self, sig: tuple[Any, ...], active: bool, macro: Any | None, prior: float, feat: np.ndarray) -> None:
        if self.disable_online_refinement:
            return
        self.online_cache[sig] = MemoizedWitness(
            bool(active),
            tuple(int(v) for v in getattr(macro, 'primitive_indices', ())) if macro is not None else tuple(),
            float(prior),
            np.asarray(feat, dtype=np.float32),
            1,
        )

    def _evaluate_one(
        self,
        planner,
        goal,
        records,
        search_state: dict[str, Any],
        h_pair,
        *,
        current_anchor: float,
        counterfactual_floor: float,
        node_ctx: dict[str, Any],
        evidence: dict[str, Any],
        scheduler_score: float,
        bridge: BridgePathCandidate,
    ) -> tuple[BridgePathCandidate, Any, float, float] | None:
        bridge_eff = bridge_efficiency(self.case, h_pair, float(current_anchor), bridge)
        feat = runtime_bridge_feature(evidence, float(current_anchor), bridge, bridge_eff=float(bridge_eff), scheduler_score=float(scheduler_score))
        sig = witness_cache_signature(
            self.case,
            self.bundle,
            node_ctx,
            evidence,
            bridge,
            cell_stride=int(self.watchdog_cfg.cell_stride),
            yaw_bins=int(self.watchdog_cfg.yaw_bins),
            scheduler_score=float(scheduler_score),
            bridge_eff=float(bridge_eff),
        )
        source, cached = self._cache_lookup(sig, feat)
        if cached is not None:
            if not bool(cached.active):
                return None
            macro = reconstruct_macro_from_indices(self.typed_macro_families, tuple(int(v) for v in cached.macro_primitive_indices))
            if macro is not None:
                review_rows = bridge_review_candidates(
                    self.case,
                    planner,
                    h_pair,
                    [(bridge, macro, float(cached.prior_score), float(_bridge_review_score(float(current_anchor), bridge)))],
                    source='bridge_review',
                )
                if review_rows:
                    final_eff = review_efficiency_for_candidate(self.case, h_pair, float(current_anchor), review_rows[0])
                    if float(final_eff) > float(counterfactual_floor):
                        self.stats['contract_pass'] = float(self.stats.get('contract_pass', 0.0) + 1.0)
                        return bridge, macro, float(cached.prior_score), float(_bridge_review_score(float(current_anchor), bridge))
                    self.stats['contract_reject'] = float(self.stats.get('contract_reject', 0.0) + 1.0)
                    if source == 'seed' and not self.disable_online_refinement:
                        self.online_cache[sig] = MemoizedWitness(False, tuple(), 0.0, np.asarray(feat, dtype=np.float32), int(cached.hits) + 1)
                    return None

        self.stats['expensive_bridge_evals'] = float(self.stats.get('expensive_bridge_evals', 0.0) + 1.0)
        srec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]), anchor=float(bridge.anchor))
        tmp_search = dict(search_state)
        tmp_search['last_record_x'] = float(srec.x)
        tmp_search['last_record_y'] = float(srec.y)
        tmp_search['last_record_yaw'] = float(srec.yaw)
        sctx = self.base.prepare_expand(planner, srec, goal, records, None, None, tmp_search, h_pair)
        if not isinstance(sctx, dict):
            self._update_online_cache(sig, False, None, 0.0, feat)
            return None
        active, macros, info = bridge_mod.compatibility_bridge_prior(
            self.case,
            self.bundle,
            sctx,
            tmp_search,
            srec,
            h_pair,
            typed_families=self.typed_macro_families,
            typed_support=self.typed_macro_support,
            replay_contract=self.replay_contract,
            macro_spec=self.macro_spec,
            watchdog_cfg=self.watchdog_cfg,
        )
        if not active or not macros:
            self._update_online_cache(sig, False, None, 0.0, feat)
            return None
        macro = macros[0]
        prior = float(info.get('compatibility_score', 0.0))
        self._update_online_cache(sig, True, macro, float(prior), feat)
        review_rows = bridge_review_candidates(
            self.case,
            planner,
            h_pair,
            [(bridge, macro, float(prior), float(_bridge_review_score(float(current_anchor), bridge)))],
            source='bridge_review',
        )
        if not review_rows:
            return None
        final_eff = review_efficiency_for_candidate(self.case, h_pair, float(current_anchor), review_rows[0])
        if float(final_eff) > float(counterfactual_floor):
            self.stats['contract_pass'] = float(self.stats.get('contract_pass', 0.0) + 1.0)
            return bridge, macro, float(prior), float(_bridge_review_score(float(current_anchor), bridge))
        self.stats['contract_reject'] = float(self.stats.get('contract_reject', 0.0) + 1.0)
        return None

    def _evaluate_paths(
        self,
        planner,
        goal,
        records,
        search_state: dict[str, Any],
        h_pair,
        *,
        current_anchor: float,
        counterfactual_floor: float,
        node_ctx: dict[str, Any],
        evidence: dict[str, Any],
        scheduler_score: float,
        paths: list[BridgePathCandidate],
    ) -> list[tuple[BridgePathCandidate, Any, float, float]]:
        out = []
        for bridge in paths:
            row = self._evaluate_one(
                planner,
                goal,
                records,
                search_state,
                h_pair,
                current_anchor=float(current_anchor),
                counterfactual_floor=float(counterfactual_floor),
                node_ctx=node_ctx,
                evidence=evidence,
                scheduler_score=float(scheduler_score),
                bridge=bridge,
            )
            if row is not None:
                out.append(row)
        return out

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            return extra
        evidence = bridge_mod.watchdog_evidence(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)
        scheduler_score = event_scheduler_score(node_ctx, evidence)
        if scheduler_score <= 0.0:
            return extra
        primitive_cands = [cand for cand in candidates if str(getattr(cand, 'source', 'primitive')) == 'primitive']
        if not primitive_cands:
            return extra
        self.stats['scheduler_hits'] = float(self.stats.get('scheduler_hits', 0.0) + 1.0)
        current_anchor, _ = h_pair(float(record.x), float(record.y), float(record.yaw))
        primitive_floor = max(review_efficiency_for_candidate(self.case, h_pair, float(current_anchor), cand) for cand in primitive_cands)
        depth1_paths = enumerate_bridge_paths(self.case, planner, h_pair, primitive_cands, max_depth=1, max_frontier=int(max(self.params.max_bridge_frontier, 1)))
        self.stats['depth1_paths'] = float(self.stats.get('depth1_paths', 0.0) + float(len(depth1_paths)))
        if not depth1_paths:
            return extra
        bridge_floor = max(bridge_efficiency(self.case, h_pair, float(current_anchor), bridge) for bridge in depth1_paths)
        counterfactual_floor = float(max(primitive_floor, bridge_floor))

        screened: list[tuple[float, bool, BridgePathCandidate]] = []
        for bridge in depth1_paths:
            bridge_eff = bridge_efficiency(self.case, h_pair, float(current_anchor), bridge)
            feat = runtime_bridge_feature(evidence, float(current_anchor), bridge, bridge_eff=float(bridge_eff), scheduler_score=float(scheduler_score))
            allow, escalate, score = prescreener_decision(self.prescreener, feat, float(scheduler_score))
            if allow:
                screened.append((float(score), bool(escalate), bridge))
        screened.sort(key=lambda item: item[0], reverse=True)
        screened = screened[: int(max(self.params.max_screened_paths, 1))]
        self.stats['screened_paths'] = float(self.stats.get('screened_paths', 0.0) + float(len(screened)))
        if not screened:
            return extra

        choices = self._evaluate_paths(
            planner,
            goal,
            records,
            search_state,
            h_pair,
            current_anchor=float(current_anchor),
            counterfactual_floor=float(counterfactual_floor),
            node_ctx=node_ctx,
            evidence=evidence,
            scheduler_score=float(scheduler_score),
            paths=[item[2] for item in screened],
        )

        need_depth2 = (not choices) and any(item[1] for item in screened)
        if need_depth2:
            self.stats['depth2_escalations'] = float(self.stats.get('depth2_escalations', 0.0) + 1.0)
            depth2_all = enumerate_bridge_paths(self.case, planner, h_pair, primitive_cands, max_depth=2, max_frontier=int(max(self.params.max_bridge_frontier, 1)))
            escalated_prefixes = {(int(item[2].primitive_indices[0]),) for item in screened if item[1]}
            depth2_paths = [path for path in depth2_all if len(path.primitive_indices) == 2 and (int(path.primitive_indices[0]),) in escalated_prefixes]
            self.stats['depth2_paths'] = float(self.stats.get('depth2_paths', 0.0) + float(len(depth2_paths)))
            if depth2_paths:
                bridge_floor = max(bridge_floor, max(bridge_efficiency(self.case, h_pair, float(current_anchor), bridge) for bridge in depth2_paths))
                counterfactual_floor = float(max(primitive_floor, bridge_floor))
                screened_depth2: list[tuple[float, BridgePathCandidate]] = []
                for bridge in depth2_paths:
                    bridge_eff = bridge_efficiency(self.case, h_pair, float(current_anchor), bridge)
                    feat = runtime_bridge_feature(evidence, float(current_anchor), bridge, bridge_eff=float(bridge_eff), scheduler_score=float(scheduler_score))
                    allow, _, score = prescreener_decision(self.prescreener, feat, float(scheduler_score))
                    if allow:
                        screened_depth2.append((float(score), bridge))
                screened_depth2.sort(key=lambda item: item[0], reverse=True)
                screened_depth2 = screened_depth2[: int(max(self.params.max_screened_paths, 1))]
                if screened_depth2:
                    choices.extend(
                        self._evaluate_paths(
                            planner,
                            goal,
                            records,
                            search_state,
                            h_pair,
                            current_anchor=float(current_anchor),
                            counterfactual_floor=float(counterfactual_floor),
                            node_ctx=node_ctx,
                            evidence=evidence,
                            scheduler_score=float(scheduler_score),
                            paths=[item[1] for item in screened_depth2],
                        )
                    )

        if not choices:
            return extra
        choices.sort(key=lambda item: (item[3], item[2]), reverse=True)
        choices = choices[: int(max(self.params.max_review_targets, 1))]
        review_rows = bridge_review_candidates(self.case, planner, h_pair, choices, source='bridge_review')
        if not review_rows:
            return extra
        extra_rows = list(extra or [])
        extra_rows.extend(review_rows)
        return extra_rows

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        base_ranked = self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        items = base_ranked if base_ranked is not None else [(cand, SuccessorDecision()) for cand in candidates]
        ranked = []
        for cand, decision in items:
            if isinstance(decision, SuccessorDecision):
                dec = {
                    'skip': bool(decision.skip),
                    'extra_edge_cost': float(decision.extra_edge_cost),
                    'priority_primary_delta': float(decision.priority_primary_delta),
                    'priority_secondary_delta': float(decision.priority_secondary_delta),
                }
            else:
                dec = dict(decision)
            if str(getattr(cand, 'source', 'primitive')) == 'bridge_review':
                prior = float((cand.sim_info or {}).get('prior_score', 0.0))
                review = float((cand.sim_info or {}).get('review_score', 0.0))
                delta = review_priority_delta(float(review), float(prior))
                dec['priority_secondary_delta'] = float(dec.get('priority_secondary_delta', 0.0)) + float(delta)
                dec['priority_primary_delta'] = float(dec.get('priority_primary_delta', 0.0)) + 0.5 * float(delta)
            ranked.append((cand, dec))
        ranked.sort(key=lambda item: float(item[1].get('priority_secondary_delta', 0.0)))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.base, 'complete_expand'):
            return self.base.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX40CSCRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SCRPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_seed_cache=bool(ablation.get('disable_seed_cache', False)),
        disable_online_refinement=bool(ablation.get('disable_online_refinement', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX40CSCRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k != 'seed_min_hits'})
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX40CSCRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k != 'seed_min_hits'})
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)
