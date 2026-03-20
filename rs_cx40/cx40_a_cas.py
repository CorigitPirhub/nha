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
from rs_cx39 import cx39_c_cbc as parent_mod
from rs_cx39.common import BridgePathCandidate, bridge_review_candidates, enumerate_bridge_paths
from rs_cx40.common import (
    BridgePrescreener,
    bridge_efficiency,
    compile_bridge_prescreener,
    event_scheduler_score,
    prescreener_decision,
    primitive_candidates_from_record,
    review_efficiency_for_candidate,
    runtime_bridge_feature,
)


@dataclass(frozen=True)
class CX40ACASParams:
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


def param_grid() -> list[CX40ACASParams]:
    return [
        CX40ACASParams(**dict(parent_params.__dict__, max_screened_paths=2))
        for parent_params in parent_mod.param_grid()
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Prescreener', 'disable_prescreener': True},
        {'name': 'No-Depth2-Escalation', 'disable_depth2_escalation': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX40ACASParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX39CCBCParams(**{k: v for k, v in params.__dict__.items() if k != 'max_screened_paths'})
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    prescreener = compile_bridge_prescreener(calib_train_assets, memory=memory, params_obj=parent_params)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx40_a_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'prescreener': {
                    'positive_hits': int(prescreener.positive_hits),
                    'negative_hits': int(prescreener.negative_hits),
                    'score_floor': float(prescreener.score_floor),
                    'depth2_floor': float(prescreener.depth2_floor),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    memory = dict(memory)
    memory['bridge_prescreener'] = prescreener
    return memory


def _bridge_review_score(current_anchor: float, bridge: BridgePathCandidate) -> float:
    return float(max(float(current_anchor) - float(bridge.anchor), 0.0) + 0.35 * max(float(current_anchor) - float(bridge.guided), 0.0))


class CASPolicy:
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX40ACASParams,
        memory: dict[str, Any],
        *,
        disable_prescreener: bool = False,
        disable_depth2_escalation: bool = False,
    ) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_prescreener = bool(disable_prescreener)
        self.disable_depth2_escalation = bool(disable_depth2_escalation)
        parent_params = parent_mod.CX39CCBCParams(**{k: v for k, v in params.__dict__.items() if k != 'max_screened_paths'})
        driver = parent_mod.CBCPolicy(case, bundle, field, parent_params, memory, disable_bridge_contract=False, max_bridge_depth_override=1)
        self.base = driver.base
        self.typed_macro_families = tuple(driver.typed_macro_families)
        self.typed_macro_support = dict(driver.typed_macro_support)
        self.replay_contract = driver.replay_contract
        self.macro_spec = driver.macro_spec
        self.watchdog_cfg = driver.watchdog_cfg
        self.prescreener: BridgePrescreener | None = memory.get('bridge_prescreener')
        self.stats: dict[str, float] = {
            'scheduler_hits': 0.0,
            'depth1_paths': 0.0,
            'screened_paths': 0.0,
            'depth2_escalations': 0.0,
            'depth2_paths': 0.0,
            'expensive_bridge_evals': 0.0,
            'contract_pass': 0.0,
            'contract_reject': 0.0,
        }

    def start_search(self, planner, start, goal, h_pair, search_state):
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        search_state['last_record_x'] = float(record.x)
        search_state['last_record_y'] = float(record.y)
        search_state['last_record_yaw'] = float(record.yaw)
        return self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

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
        paths: list[BridgePathCandidate],
        screened_only: bool,
        allow_escalation_flags: dict[tuple[int, ...], bool],
    ) -> list[tuple[BridgePathCandidate, Any, float, float]]:
        choices: list[tuple[BridgePathCandidate, Any, float, float]] = []
        for bridge in paths:
            if screened_only and not allow_escalation_flags.get(tuple(int(v) for v in bridge.primitive_indices), False):
                continue
            self.stats['expensive_bridge_evals'] = float(self.stats.get('expensive_bridge_evals', 0.0) + 1.0)
            srec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]), anchor=float(bridge.anchor))
            tmp_search = dict(search_state)
            tmp_search['last_record_x'] = float(srec.x)
            tmp_search['last_record_y'] = float(srec.y)
            tmp_search['last_record_yaw'] = float(srec.yaw)
            sctx = self.base.prepare_expand(planner, srec, goal, records, None, None, tmp_search, h_pair)
            if not isinstance(sctx, dict):
                continue
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
                continue
            review_rows = bridge_review_candidates(
                self.case,
                planner,
                h_pair,
                [(bridge, macros[0], float(info.get('compatibility_score', 0.0)), float(_bridge_review_score(float(current_anchor), bridge)))],
                source='bridge_review',
            )
            if not review_rows:
                continue
            final_eff = review_efficiency_for_candidate(self.case, h_pair, float(current_anchor), review_rows[0])
            if float(final_eff) > float(counterfactual_floor):
                self.stats['contract_pass'] = float(self.stats.get('contract_pass', 0.0) + 1.0)
                choices.append((bridge, macros[0], float(info.get('compatibility_score', 0.0)), float(_bridge_review_score(float(current_anchor), bridge))))
            else:
                self.stats['contract_reject'] = float(self.stats.get('contract_reject', 0.0) + 1.0)
        return choices

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

        depth1_paths = enumerate_bridge_paths(
            self.case,
            planner,
            h_pair,
            primitive_cands,
            max_depth=1,
            max_frontier=int(max(self.params.max_bridge_frontier, 1)),
        )
        self.stats['depth1_paths'] = float(self.stats.get('depth1_paths', 0.0) + float(len(depth1_paths)))
        if not depth1_paths:
            return extra
        bridge_floor = max(bridge_efficiency(self.case, h_pair, float(current_anchor), bridge) for bridge in depth1_paths)
        counterfactual_floor = float(max(primitive_floor, bridge_floor))

        screened: list[tuple[float, bool, BridgePathCandidate]] = []
        allow_keys: dict[tuple[int, ...], bool] = {}
        for bridge in depth1_paths:
            bridge_eff = bridge_efficiency(self.case, h_pair, float(current_anchor), bridge)
            feat = runtime_bridge_feature(evidence, float(current_anchor), bridge, bridge_eff=float(bridge_eff), scheduler_score=float(scheduler_score))
            if self.disable_prescreener:
                allow, escalate, score = True, True, 1.0
            else:
                allow, escalate, score = prescreener_decision(self.prescreener, feat, float(scheduler_score))
            if allow:
                screened.append((float(score), bool(escalate), bridge))
                allow_keys[tuple(int(v) for v in bridge.primitive_indices)] = True
        screened.sort(key=lambda item: item[0], reverse=True)
        screened = screened[: int(max(self.params.max_screened_paths, 1))]
        self.stats['screened_paths'] = float(self.stats.get('screened_paths', 0.0) + float(len(screened)))
        if not screened:
            return extra

        depth1_choices = self._evaluate_paths(
            planner,
            goal,
            records,
            search_state,
            h_pair,
            current_anchor=float(current_anchor),
            counterfactual_floor=float(counterfactual_floor),
            paths=[item[2] for item in screened],
            screened_only=False,
            allow_escalation_flags={tuple(int(v) for v in item[2].primitive_indices): True for item in screened},
        )
        choices = list(depth1_choices)

        need_depth2 = (not choices) and (not self.disable_depth2_escalation) and any(item[1] for item in screened)
        if need_depth2:
            self.stats['depth2_escalations'] = float(self.stats.get('depth2_escalations', 0.0) + 1.0)
            depth2_all = enumerate_bridge_paths(
                self.case,
                planner,
                h_pair,
                primitive_cands,
                max_depth=2,
                max_frontier=int(max(self.params.max_bridge_frontier, 1)),
            )
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
                    if self.disable_prescreener:
                        allow, score = True, 1.0
                    else:
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
                            paths=[item[1] for item in screened_depth2],
                            screened_only=False,
                            allow_escalation_flags={tuple(int(v) for v in item[1].primitive_indices): True for item in screened_depth2},
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


def make_policy(memory: dict[str, Any], params: CX40ACASParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CASPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_prescreener=bool(ablation.get('disable_prescreener', False)),
        disable_depth2_escalation=bool(ablation.get('disable_depth2_escalation', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX40ACASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX39CCBCParams(**{k: v for k, v in params.__dict__.items() if k != 'max_screened_paths'})
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX40ACASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX39CCBCParams(**{k: v for k, v in params.__dict__.items() if k != 'max_screened_paths'})
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)
