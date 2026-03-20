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
from rs_cx39.common import bridge_review_candidates
from rs_cx40 import cx40_a_cas as parent_mod
from rs_cx40.common import (
    bridge_efficiency,
    compile_bridge_prescreener,
    event_scheduler_score,
    prescreener_decision,
    review_efficiency_for_candidate,
    runtime_bridge_feature,
)
from rs_cx41.common import SubstrateBridgeNode, build_substrate_frontier


@dataclass(frozen=True)
class CX41ASBNParams:
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


def param_grid() -> list[CX41ASBNParams]:
    return [CX41ASBNParams(**params.__dict__) for params in parent_mod.param_grid()]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Substrate-Quotient', 'disable_substrate_quotient': True},
        {'name': 'No-Depth2-Escalation', 'disable_depth2_escalation': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX41ASBNParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX40ACASParams(**params.__dict__)
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    # reuse the same prescreener contract so the only new variable is substrate factoring
    if 'bridge_prescreener' not in memory:
        memory = dict(memory)
        memory['bridge_prescreener'] = compile_bridge_prescreener(calib_train_assets, memory=memory, params_obj=parent_params)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx41_a_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'prescreener': {
                    'positive_hits': int(memory['bridge_prescreener'].positive_hits),
                    'negative_hits': int(memory['bridge_prescreener'].negative_hits),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return memory


def _bridge_review_score(current_anchor: float, node: SubstrateBridgeNode) -> float:
    return float(max(float(current_anchor) - float(node.path.anchor), 0.0) + 0.35 * max(float(current_anchor) - float(node.path.guided), 0.0))


class SBNPolicy:
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX41ASBNParams,
        memory: dict[str, Any],
        *,
        disable_substrate_quotient: bool = False,
        disable_depth2_escalation: bool = False,
    ) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_substrate_quotient = bool(disable_substrate_quotient)
        self.disable_depth2_escalation = bool(disable_depth2_escalation)
        parent_params = parent_mod.CX40ACASParams(**params.__dict__)
        driver = parent_mod.CASPolicy(case, bundle, field, parent_params, memory, disable_prescreener=False, disable_depth2_escalation=False)
        self.base = driver.base
        self.typed_macro_families = tuple(driver.typed_macro_families)
        self.typed_macro_support = dict(driver.typed_macro_support)
        self.replay_contract = driver.replay_contract
        self.macro_spec = driver.macro_spec
        self.watchdog_cfg = driver.watchdog_cfg
        self.prescreener = memory['bridge_prescreener']
        self.stats: dict[str, float] = {
            'scheduler_hits': 0.0,
            'raw_bridge_paths': 0.0,
            'substrate_nodes': 0.0,
            'screened_nodes': 0.0,
            'depth2_escalations': 0.0,
            'expensive_substrate_evals': 0.0,
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

    def _evaluate_nodes(
        self,
        planner,
        goal,
        records,
        search_state: dict[str, Any],
        h_pair,
        *,
        current_anchor: float,
        counterfactual_floor: float,
        nodes: list[SubstrateBridgeNode],
    ) -> list[tuple[Any, Any, float, float]]:
        out: list[tuple[Any, Any, float, float]] = []
        for node in nodes:
            self.stats['expensive_substrate_evals'] = float(self.stats.get('expensive_substrate_evals', 0.0) + 1.0)
            srec = SimpleNamespace(x=float(node.path.next_state[0]), y=float(node.path.next_state[1]), yaw=float(node.path.next_state[2]), anchor=float(node.path.anchor))
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
                [(node.path, macros[0], float(info.get('compatibility_score', 0.0)), float(_bridge_review_score(float(current_anchor), node)))],
                source='bridge_review',
            )
            if not review_rows:
                continue
            final_eff = review_efficiency_for_candidate(self.case, h_pair, float(current_anchor), review_rows[0])
            if float(final_eff) > float(counterfactual_floor):
                self.stats['contract_pass'] = float(self.stats.get('contract_pass', 0.0) + 1.0)
                out.append((node.path, macros[0], float(info.get('compatibility_score', 0.0)), float(_bridge_review_score(float(current_anchor), node))))
            else:
                self.stats['contract_reject'] = float(self.stats.get('contract_reject', 0.0) + 1.0)
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

        if self.disable_substrate_quotient:
            nodes = [SubstrateBridgeNode((idx, idx, idx), len(path.primitive_indices), path, float(bridge_efficiency(self.case, h_pair, float(current_anchor), path))) for idx, path in enumerate(bridge_mod.enumerate_bridge_paths(self.case, planner, h_pair, primitive_cands, max_depth=1, max_frontier=int(max(self.params.max_bridge_frontier, 1))))] if hasattr(bridge_mod, 'enumerate_bridge_paths') else []
        else:
            nodes = build_substrate_frontier(
                self.case,
                planner,
                h_pair,
                primitive_cands,
                current_anchor=float(current_anchor),
                cell_stride=int(self.params.cell_stride),
                yaw_bins=int(self.params.yaw_bins),
                max_depth=1,
                max_frontier=int(max(self.params.max_bridge_frontier, 1)),
            )
        self.stats['substrate_nodes'] = float(self.stats.get('substrate_nodes', 0.0) + float(len(nodes)))
        self.stats['raw_bridge_paths'] = float(self.stats.get('raw_bridge_paths', 0.0) + float(len(primitive_cands) * max(int(self.params.max_bridge_depth), 1)))
        if not nodes:
            return extra
        bridge_floor = max(float(node.bridge_eff) for node in nodes)
        counterfactual_floor = float(max(primitive_floor, bridge_floor))

        screened: list[tuple[float, bool, SubstrateBridgeNode]] = []
        for node in nodes:
            feat = runtime_bridge_feature(evidence, float(current_anchor), node.path, bridge_eff=float(node.bridge_eff), scheduler_score=float(scheduler_score))
            allow, escalate, score = prescreener_decision(self.prescreener, feat, float(scheduler_score))
            if allow:
                screened.append((float(score), bool(escalate), node))
        screened.sort(key=lambda item: item[0], reverse=True)
        screened = screened[: int(max(self.params.max_screened_paths, 1))]
        self.stats['screened_nodes'] = float(self.stats.get('screened_nodes', 0.0) + float(len(screened)))
        if not screened:
            return extra

        choices = self._evaluate_nodes(
            planner,
            goal,
            records,
            search_state,
            h_pair,
            current_anchor=float(current_anchor),
            counterfactual_floor=float(counterfactual_floor),
            nodes=[item[2] for item in screened],
        )

        need_depth2 = (not choices) and (not self.disable_depth2_escalation) and any(item[1] for item in screened)
        if need_depth2:
            self.stats['depth2_escalations'] = float(self.stats.get('depth2_escalations', 0.0) + 1.0)
            depth2_nodes = build_substrate_frontier(
                self.case,
                planner,
                h_pair,
                primitive_cands,
                current_anchor=float(current_anchor),
                cell_stride=int(self.params.cell_stride),
                yaw_bins=int(self.params.yaw_bins),
                max_depth=2,
                max_frontier=int(max(self.params.max_bridge_frontier, 1)),
            )
            depth2_nodes = [node for node in depth2_nodes if int(node.depth) == 2]
            if depth2_nodes:
                bridge_floor = max(bridge_floor, max(float(node.bridge_eff) for node in depth2_nodes))
                counterfactual_floor = float(max(primitive_floor, bridge_floor))
                screened_depth2: list[tuple[float, SubstrateBridgeNode]] = []
                for node in depth2_nodes:
                    feat = runtime_bridge_feature(evidence, float(current_anchor), node.path, bridge_eff=float(node.bridge_eff), scheduler_score=float(scheduler_score))
                    allow, _, score = prescreener_decision(self.prescreener, feat, float(scheduler_score))
                    if allow:
                        screened_depth2.append((float(score), node))
                screened_depth2.sort(key=lambda item: item[0], reverse=True)
                screened_depth2 = screened_depth2[: int(max(self.params.max_screened_paths, 1))]
                if screened_depth2:
                    choices.extend(
                        self._evaluate_nodes(
                            planner,
                            goal,
                            records,
                            search_state,
                            h_pair,
                            current_anchor=float(current_anchor),
                            counterfactual_floor=float(counterfactual_floor),
                            nodes=[item[1] for item in screened_depth2],
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


def make_policy(memory: dict[str, Any], params: CX41ASBNParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SBNPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_substrate_quotient=bool(ablation.get('disable_substrate_quotient', False)),
        disable_depth2_escalation=bool(ablation.get('disable_depth2_escalation', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX41ASBNParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX40ACASParams(**params.__dict__)
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX41ASBNParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX40ACASParams(**params.__dict__)
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)

