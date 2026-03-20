from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorDecision
from rs_cx.common import CXGlobalConfig
from rs_cx11.common import support_match
from rs_cx23.common import class_key
from rs_cx27.common import watchdog_evidence
from rs_cx34.common import CX34SliceSpec, scene_match
from rs_cx35.common import best_macro_score_for_family, choose_typed_family
from rs_cx36 import cx36_b_etc as parent_mod
from rs_cx36.common import best_primitive_score
from rs_cx37 import cx37_a_rpt as replay_parent
from rs_cx37.common import replay_feature, replay_priority_prior
from rs_cx38.common import review_priority_delta
from rs_cx39.common import bridge_review_candidates, enumerate_bridge_paths


@dataclass(frozen=True)
class CX39BCBSParams:
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


def param_grid() -> list[CX39BCBSParams]:
    return [
        CX39BCBSParams(
            0.10,
            0.36,
            0.08,
            0.39,
            0.99,
            1,
            0.11,
            0.13,
            0.31,
            0.97,
            0.125,
            0.34,
            0.97,
            0.078,
            0.095,
            0.34,
            0.37,
            0.97,
            1.01,
            2,
            18,
            0.10,
            0.54,
            0.02,
            0.05,
            32,
            16,
            2,
            24,
            2,
            2,
            3,
            3,
        ),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Depth2-Bridge', 'max_bridge_depth_override': 1},
        {'name': 'No-Compatibility-Witness', 'disable_compatibility_witness': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX39BCBSParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    replay_params = replay_parent.CX37ARPTParams(
        turn_bridge_max=float(params.turn_bridge_max),
        turn_focus_max=float(params.turn_focus_max),
        rescue_bridge_max=float(params.rescue_bridge_max),
        rescue_focus_min=float(params.rescue_focus_min),
        rescue_path_min=float(params.rescue_path_min),
        rescue_budget=int(params.rescue_budget),
        suppress_bridge_min=float(params.suppress_bridge_min),
        suppress_bridge_max=float(params.suppress_bridge_max),
        suppress_focus_max=float(params.suppress_focus_max),
        suppress_path_min=float(params.suppress_path_min),
        stubborn_bridge_min=float(params.stubborn_bridge_min),
        stubborn_focus_max=float(params.stubborn_focus_max),
        stubborn_path_max=float(params.stubborn_path_max),
        macro_bridge_min=float(params.macro_bridge_min),
        macro_bridge_max=float(params.macro_bridge_max),
        macro_focus_min=float(params.macro_focus_min),
        macro_focus_max=float(params.macro_focus_max),
        macro_path_min=float(params.macro_path_min),
        macro_path_max=float(params.macro_path_max),
        maze_revisit_thr=int(params.maze_revisit_thr),
        maze_stall_steps=int(params.maze_stall_steps),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_thr=float(params.trap_thr),
        progress_eps=float(params.progress_eps),
        commit_fail_margin=float(params.commit_fail_margin),
        failure_ttl=int(params.failure_ttl),
        history_window=int(params.history_window),
        cell_stride=int(params.cell_stride),
        yaw_bins=int(params.yaw_bins),
        min_hits=int(params.min_hits),
    )
    return replay_parent.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, replay_params, out_dir, device, dependencies)


def _event_score(evidence: dict[str, Any]) -> float:
    return float(
        0.30 * min(float(evidence.get('stall_steps', 0)) / 4.0, 1.0)
        + 0.25 * min(float(evidence.get('class_churn', 0.0)) / 0.5, 1.0)
        + 0.20 * min(float(evidence.get('loop_rate', 0.0)) / 0.2, 1.0)
        + 0.15 * min(float(evidence.get('recent_failures', 0)) / 2.0, 1.0)
        + 0.10 * float(1.0 if bool(evidence.get('blocklist_hit', False)) else 0.0)
    )


def compatibility_bridge_prior(
    case: dict[str, Any],
    bundle: dict[str, Any],
    ctx: dict[str, Any],
    search_state: dict[str, Any],
    record,
    h_pair,
    *,
    typed_families: tuple[Any, ...],
    typed_support: dict[str, Any],
    replay_contract,
    macro_spec: CX34SliceSpec,
    watchdog_cfg,
) -> tuple[bool, list[Any], dict[str, Any]]:
    if str(case.get('scenario', '')) == 'parasol_misc' and scene_match(bundle, macro_spec):
        return False, [], {'reason': 'in_slice'}
    evidence = watchdog_evidence(search_state, record, case, bundle, ctx, watchdog_cfg)
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
    event_score = _event_score(evidence)
    compatibility_score = float(0.50 * margin_score + 0.30 * float(pos_sim if pos_match else 0.0) + 0.20 * event_score)
    active = bool(((pos_match and not neg_match) or margin >= float(replay_contract.high_margin_floor)) and not neg_match and compatibility_score > 0.0)
    return active, macros if active else [], {
        'family_name': family_name,
        'margin': float(margin),
        'primitive_best': float(primitive_best),
        'macro_best': float(max(macro_scores)),
        'event_score': float(event_score),
        'margin_score': float(margin_score),
        'compatibility_score': float(compatibility_score),
        'pos_match': bool(pos_match),
        'neg_match': bool(neg_match),
        'pos_sim': float(pos_sim),
        'neg_sim': float(neg_sim),
    }


class CBSPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX39BCBSParams, memory: dict[str, Any], disable_compatibility_witness: bool = False, max_bridge_depth_override: int | None = None) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_compatibility_witness = bool(disable_compatibility_witness)
        self.max_bridge_depth = int(max_bridge_depth_override) if max_bridge_depth_override is not None else int(params.max_bridge_depth)
        self.typed_macro_families = tuple(memory['typed_macro_families'])
        self.typed_macro_support = dict(memory['typed_macro_support'])
        self.replay_contract = memory['replay_contract']
        self.macro_spec = CX34SliceSpec(
            bridge_min=float(params.macro_bridge_min),
            bridge_max=float(params.macro_bridge_max),
            focus_min=float(params.macro_focus_min),
            focus_max=float(params.macro_focus_max),
            path_min=float(params.macro_path_min),
            path_max=float(params.macro_path_max),
        )
        self.watchdog_cfg = replay_parent.CX27WatchdogConfig(
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
        )
        self.base = parent_mod.make_policy(
            {
                'haa_teacher': memory['haa_teacher'],
                'typed_macro_families': memory['typed_macro_families'],
                'typed_macro_support': memory['typed_macro_support'],
                'event_contract': None,
            },
            parent_mod.CX36BETCParams(
                turn_bridge_max=float(params.turn_bridge_max),
                turn_focus_max=float(params.turn_focus_max),
                rescue_bridge_max=float(params.rescue_bridge_max),
                rescue_focus_min=float(params.rescue_focus_min),
                rescue_path_min=float(params.rescue_path_min),
                rescue_budget=int(params.rescue_budget),
                suppress_bridge_min=float(params.suppress_bridge_min),
                suppress_bridge_max=float(params.suppress_bridge_max),
                suppress_focus_max=float(params.suppress_focus_max),
                suppress_path_min=float(params.suppress_path_min),
                stubborn_bridge_min=float(params.stubborn_bridge_min),
                stubborn_focus_max=float(params.stubborn_focus_max),
                stubborn_path_max=float(params.stubborn_path_max),
                macro_bridge_min=float(params.macro_bridge_min),
                macro_bridge_max=float(params.macro_bridge_max),
                macro_focus_min=float(params.macro_focus_min),
                macro_focus_max=float(params.macro_focus_max),
                macro_path_min=float(params.macro_path_min),
                macro_path_max=float(params.macro_path_max),
                maze_revisit_thr=int(params.maze_revisit_thr),
                maze_stall_steps=int(params.maze_stall_steps),
                reverse_required_thr=float(params.reverse_required_thr),
                trap_thr=float(params.trap_thr),
                progress_eps=float(params.progress_eps),
                commit_fail_margin=float(params.commit_fail_margin),
                failure_ttl=int(params.failure_ttl),
                history_window=int(params.history_window),
                cell_stride=int(params.cell_stride),
                yaw_bins=int(params.yaw_bins),
                min_hits=int(params.min_hits),
            ),
            case,
            bundle,
            field,
            'cpu',
            ablation={'disable_event_trigger': True},
        )
        self.stats: dict[str, float] = {
            'bridge_scheduler_hits': 0.0,
            'bridge_paths': 0.0,
            'bridge_active_hits': 0.0,
            'bridge_review_candidates': 0.0,
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
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)
        scheduler_score = max(_event_score(evidence), 0.4 if str(class_key(node_ctx)) == 'uncertain|none' else 0.0)
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
            if self.disable_compatibility_witness:
                active, macros, info = replay_priority_prior(
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
                prior_score = float(info.get('prior_score', 0.0))
            else:
                active, macros, info = compatibility_bridge_prior(
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
                prior_score = float(info.get('compatibility_score', 0.0))
            if not active or not macros:
                reason = str(info.get('reason', 'inactive'))
                key = f'inactive_reason:{reason}'
                self.stats[key] = float(self.stats.get(key, 0.0) + 1.0)
                continue
            self.stats['bridge_active_hits'] = float(self.stats.get('bridge_active_hits', 0.0) + 1.0)
            review_score = float(max(current_anchor - float(bridge.anchor), 0.0) + 0.35 * max(current_anchor - float(bridge.guided), 0.0))
            bridge_choices.append((bridge, macros[0], float(prior_score), float(review_score)))
        if not bridge_choices:
            return extra
        bridge_choices.sort(key=lambda item: (item[3], item[2]), reverse=True)
        bridge_choices = bridge_choices[: int(max(self.params.max_review_targets, 1))]
        review_rows = bridge_review_candidates(self.case, planner, h_pair, bridge_choices, source='bridge_review')
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


def make_policy(memory: dict[str, Any], params: CX39BCBSParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CBSPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_compatibility_witness=bool(ablation.get('disable_compatibility_witness', False)),
        max_bridge_depth_override=int(ablation['max_bridge_depth_override']) if 'max_bridge_depth_override' in ablation else None,
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX39BCBSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(
        case,
        predictor,
        cfg,
        parent_mod.CX36BETCParams(
            turn_bridge_max=float(params.turn_bridge_max),
            turn_focus_max=float(params.turn_focus_max),
            rescue_bridge_max=float(params.rescue_bridge_max),
            rescue_focus_min=float(params.rescue_focus_min),
            rescue_path_min=float(params.rescue_path_min),
            rescue_budget=int(params.rescue_budget),
            suppress_bridge_min=float(params.suppress_bridge_min),
            suppress_bridge_max=float(params.suppress_bridge_max),
            suppress_focus_max=float(params.suppress_focus_max),
            suppress_path_min=float(params.suppress_path_min),
            stubborn_bridge_min=float(params.stubborn_bridge_min),
            stubborn_focus_max=float(params.stubborn_focus_max),
            stubborn_path_max=float(params.stubborn_path_max),
            macro_bridge_min=float(params.macro_bridge_min),
            macro_bridge_max=float(params.macro_bridge_max),
            macro_focus_min=float(params.macro_focus_min),
            macro_focus_max=float(params.macro_focus_max),
            macro_path_min=float(params.macro_path_min),
            macro_path_max=float(params.macro_path_max),
            maze_revisit_thr=int(params.maze_revisit_thr),
            maze_stall_steps=int(params.maze_stall_steps),
            reverse_required_thr=float(params.reverse_required_thr),
            trap_thr=float(params.trap_thr),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            min_hits=int(params.min_hits),
        ),
        {'haa_teacher': memory['haa_teacher'], 'typed_macro_families': memory['typed_macro_families'], 'typed_macro_support': memory['typed_macro_support']},
    )


def build_standard_field(sample, predictor, params: CX39BCBSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(
        sample,
        predictor,
        parent_mod.CX36BETCParams(
            turn_bridge_max=float(params.turn_bridge_max),
            turn_focus_max=float(params.turn_focus_max),
            rescue_bridge_max=float(params.rescue_bridge_max),
            rescue_focus_min=float(params.rescue_focus_min),
            rescue_path_min=float(params.rescue_path_min),
            rescue_budget=int(params.rescue_budget),
            suppress_bridge_min=float(params.suppress_bridge_min),
            suppress_bridge_max=float(params.suppress_bridge_max),
            suppress_focus_max=float(params.suppress_focus_max),
            suppress_path_min=float(params.suppress_path_min),
            stubborn_bridge_min=float(params.stubborn_bridge_min),
            stubborn_focus_max=float(params.stubborn_focus_max),
            stubborn_path_max=float(params.stubborn_path_max),
            macro_bridge_min=float(params.macro_bridge_min),
            macro_bridge_max=float(params.macro_bridge_max),
            macro_focus_min=float(params.macro_focus_min),
            macro_focus_max=float(params.macro_focus_max),
            macro_path_min=float(params.macro_path_min),
            macro_path_max=float(params.macro_path_max),
            maze_revisit_thr=int(params.maze_revisit_thr),
            maze_stall_steps=int(params.maze_stall_steps),
            reverse_required_thr=float(params.reverse_required_thr),
            trap_thr=float(params.trap_thr),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            min_hits=int(params.min_hits),
        ),
        {'haa_teacher': memory['haa_teacher'], 'typed_macro_families': memory['typed_macro_families'], 'typed_macro_support': memory['typed_macro_support']},
    ).astype(np.float32)
