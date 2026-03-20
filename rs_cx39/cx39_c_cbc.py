from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorCandidate, SuccessorDecision
from rs_cx.common import CXGlobalConfig
from rs_cx38.common import bounded_local_review_score, review_priority_delta
from rs_cx39 import cx39_b_cbs as parent_mod
from rs_cx39.common import BridgePathCandidate, bridge_review_candidates, enumerate_bridge_paths


@dataclass(frozen=True)
class CX39CCBCParams:
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


def param_grid() -> list[CX39CCBCParams]:
    return [
        CX39CCBCParams(**params.__dict__)
        for params in parent_mod.param_grid()
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Bridge-Contract', 'disable_bridge_contract': True},
        {'name': 'No-Depth2-Bridge', 'max_bridge_depth_override': 1},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX39CCBCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX39BCBSParams(**params.__dict__)
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir, device, dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx39_c_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'replay_contract': {
                    'positive_hits': int(memory['replay_contract'].positive_hits),
                    'negative_hits': int(memory['replay_contract'].negative_hits),
                    'margin_floor': float(memory['replay_contract'].margin_floor),
                    'high_margin_floor': float(memory['replay_contract'].high_margin_floor),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return memory


def _review_efficiency(case: dict[str, Any], h_pair, current_anchor: float, cand: SuccessorCandidate) -> float:
    raw = float(bounded_local_review_score(case, h_pair, float(current_anchor), cand))
    return float(raw / max(float(getattr(cand, 'edge_cost', 0.0)), 1e-6))


def _bridge_candidate_from_path(bridge: BridgePathCandidate) -> SuccessorCandidate:
    return SuccessorCandidate(
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


class CBCPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX39CCBCParams, memory: dict[str, Any], disable_bridge_contract: bool = False, max_bridge_depth_override: int | None = None) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_bridge_contract = bool(disable_bridge_contract)
        base_params = parent_mod.CX39BCBSParams(**params.__dict__)
        driver = parent_mod.CBSPolicy(
            case,
            bundle,
            field,
            base_params,
            memory,
            disable_compatibility_witness=True,
            max_bridge_depth_override=max_bridge_depth_override,
        )
        self.base = driver.base
        self.typed_macro_families = tuple(driver.typed_macro_families)
        self.typed_macro_support = dict(driver.typed_macro_support)
        self.replay_contract = driver.replay_contract
        self.macro_spec = driver.macro_spec
        self.watchdog_cfg = driver.watchdog_cfg
        self.max_bridge_depth = int(max_bridge_depth_override) if max_bridge_depth_override is not None else int(params.max_bridge_depth)
        self.stats: dict[str, float] = {
            'bridge_scheduler_hits': 0.0,
            'bridge_paths': 0.0,
            'bridge_active_hits': 0.0,
            'bridge_review_candidates': 0.0,
            'bridge_contract_pass': 0.0,
            'bridge_contract_reject': 0.0,
        }

    def start_search(self, planner, start, goal, h_pair, search_state):
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        search_state['last_record_x'] = float(record.x)
        search_state['last_record_y'] = float(record.y)
        search_state['last_record_yaw'] = float(record.yaw)
        return self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            return extra
        evidence = parent_mod.watchdog_evidence(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)
        scheduler_score = max(parent_mod._event_score(evidence), 0.4 if str(parent_mod.class_key(node_ctx)) == 'uncertain|none' else 0.0)
        if scheduler_score <= 0.0:
            return extra
        primitive_cands = [cand for cand in candidates if str(getattr(cand, 'source', 'primitive')) == 'primitive']
        if not primitive_cands:
            return extra
        self.stats['bridge_scheduler_hits'] = float(self.stats.get('bridge_scheduler_hits', 0.0) + 1.0)
        bridge_paths = enumerate_bridge_paths(
            self.case,
            planner,
            h_pair,
            primitive_cands,
            max_depth=int(max(self.max_bridge_depth, 1)),
            max_frontier=int(max(self.params.max_bridge_frontier, 1)),
        )
        self.stats['bridge_paths'] = float(self.stats.get('bridge_paths', 0.0) + float(len(bridge_paths)))
        if not bridge_paths:
            return extra

        current_anchor, _ = h_pair(float(record.x), float(record.y), float(record.yaw))
        primitive_floor = max(_review_efficiency(self.case, h_pair, float(current_anchor), cand) for cand in primitive_cands)
        bridge_floor = max(_review_efficiency(self.case, h_pair, float(current_anchor), _bridge_candidate_from_path(bridge)) for bridge in bridge_paths)
        counterfactual_floor = float(max(primitive_floor, bridge_floor))

        bridge_choices: list[tuple[Any, Any, float, float]] = []
        for bridge in bridge_paths:
            srec = SimpleNamespace(x=float(bridge.next_state[0]), y=float(bridge.next_state[1]), yaw=float(bridge.next_state[2]), anchor=float(bridge.anchor))
            tmp_search = dict(search_state)
            tmp_search['last_record_x'] = float(srec.x)
            tmp_search['last_record_y'] = float(srec.y)
            tmp_search['last_record_yaw'] = float(srec.yaw)
            sctx = self.base.prepare_expand(planner, srec, goal, records, None, None, tmp_search, h_pair)
            if not isinstance(sctx, dict):
                continue
            active, macros, info = parent_mod.compatibility_bridge_prior(
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
                reason = str(info.get('reason', 'inactive'))
                key = f'inactive_reason:{reason}'
                self.stats[key] = float(self.stats.get(key, 0.0) + 1.0)
                continue
            self.stats['bridge_active_hits'] = float(self.stats.get('bridge_active_hits', 0.0) + 1.0)
            review_score = float(max(current_anchor - float(bridge.anchor), 0.0) + 0.35 * max(current_anchor - float(bridge.guided), 0.0))
            bridge_choices.append((bridge, macros[0], float(info.get('compatibility_score', 0.0)), float(review_score)))
        if not bridge_choices:
            return extra

        bridge_choices.sort(key=lambda item: (item[3], item[2]), reverse=True)
        bridge_choices = bridge_choices[: int(max(self.params.max_review_targets, 1))]
        review_rows = bridge_review_candidates(self.case, planner, h_pair, bridge_choices, source='bridge_review')
        if not self.disable_bridge_contract:
            filtered = []
            for row in review_rows:
                eff = _review_efficiency(self.case, h_pair, float(current_anchor), row)
                if float(eff) > float(counterfactual_floor):
                    filtered.append(row)
                    self.stats['bridge_contract_pass'] = float(self.stats.get('bridge_contract_pass', 0.0) + 1.0)
                else:
                    self.stats['bridge_contract_reject'] = float(self.stats.get('bridge_contract_reject', 0.0) + 1.0)
            review_rows = filtered
        if not review_rows:
            return extra
        self.stats['bridge_review_candidates'] = float(self.stats.get('bridge_review_candidates', 0.0) + float(len(review_rows)))
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


def make_policy(memory: dict[str, Any], params: CX39CCBCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CBCPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_bridge_contract=bool(ablation.get('disable_bridge_contract', False)),
        max_bridge_depth_override=int(ablation['max_bridge_depth_override']) if 'max_bridge_depth_override' in ablation else None,
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX39CCBCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX39BCBSParams(**params.__dict__)
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX39CCBCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX39BCBSParams(**params.__dict__)
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)
