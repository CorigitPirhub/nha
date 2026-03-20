from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorDecision
from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx34.common import CX34SliceSpec
from rs_cx36 import cx36_b_etc as parent_mod
from rs_cx37 import cx37_a_rpt as replay_parent
from rs_cx37.common import replay_priority_prior
from rs_cx38.common import bounded_local_review_score, review_priority_delta
from rs_cx39.common import detour_review_candidates


@dataclass(frozen=True)
class CX39ADRGParams:
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
    max_review_targets: int


def param_grid() -> list[CX39ADRGParams]:
    return [
        CX39ADRGParams(
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
        ),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Detour-Generator', 'disable_detour_generator': True},
        {'name': 'No-Review-Prior', 'disable_review_prior': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX39ADRGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
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


class DRGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX39ADRGParams, memory: dict[str, Any], disable_detour_generator: bool = False, disable_review_prior: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_detour_generator = bool(disable_detour_generator)
        self.disable_review_prior = bool(disable_review_prior)
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
        self.stats: dict[str, float] = {
            'uncertain_nodes': 0.0,
            'primitive_sibling_evals': 0.0,
            'replay_active_hits': 0.0,
            'review_target_batches': 0.0,
            'review_targets': 0.0,
            'review_candidates': 0.0,
            'review_expanded_hits': 0.0,
        }

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('_cx39_review_keys', set())
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        search_state['last_record_x'] = float(record.x)
        search_state['last_record_y'] = float(record.y)
        search_state['last_record_yaw'] = float(record.yaw)
        review_keys = search_state.get('_cx39_review_keys', set())
        try:
            state_key = planner._state_key(float(record.x), float(record.y), float(record.yaw))
        except Exception:
            state_key = None
        if state_key is not None and state_key in review_keys:
            self.stats['review_expanded_hits'] = float(self.stats.get('review_expanded_hits', 0.0) + 1.0)
        ctx = self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict):
            ctx.pop('_cx39_review_targets', None)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_detour_generator or not isinstance(node_ctx, dict):
            return extra
        if str(class_key(node_ctx)) != 'uncertain|none':
            return extra
        self.stats['uncertain_nodes'] = float(self.stats.get('uncertain_nodes', 0.0) + 1.0)
        primitive_cands = [cand for cand in candidates if str(getattr(cand, 'source', 'primitive')) == 'primitive']
        if not primitive_cands:
            return extra
        review_targets: list[tuple[Any, Any, float, float]] = []
        for cand in primitive_cands:
            self.stats['primitive_sibling_evals'] = float(self.stats.get('primitive_sibling_evals', 0.0) + 1.0)
            srec = SimpleNamespace(x=float(cand.next_state[0]), y=float(cand.next_state[1]), yaw=float(cand.next_state[2]), anchor=float(cand.anchor))
            tmp_search = dict(search_state)
            tmp_search['last_record_x'] = float(srec.x)
            tmp_search['last_record_y'] = float(srec.y)
            tmp_search['last_record_yaw'] = float(srec.yaw)
            sctx = self.base.prepare_expand(planner, srec, goal, records, None, None, tmp_search, h_pair)
            if not isinstance(sctx, dict):
                continue
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
            if not active or not macros:
                reason = str(info.get('reason', 'inactive'))
                key = f'inactive_reason:{reason}'
                self.stats[key] = float(self.stats.get(key, 0.0) + 1.0)
                continue
            self.stats['replay_active_hits'] = float(self.stats.get('replay_active_hits', 0.0) + 1.0)
            prior_score = float(info.get('prior_score', 0.0))
            review_score = 0.0
            current_anchor, _ = h_pair(float(record.x), float(record.y), float(record.yaw))
            if not self.disable_review_prior:
                review_score = max(bounded_local_review_score(self.case, h_pair, float(current_anchor), cand), 0.0)
            review_targets.append((cand, macros[0], float(prior_score), float(review_score)))
        if not review_targets:
            return extra
        review_targets.sort(key=lambda item: (item[3], item[2]), reverse=True)
        review_targets = review_targets[: int(max(self.params.max_review_targets, 1))]
        self.stats['review_target_batches'] = float(self.stats.get('review_target_batches', 0.0) + 1.0)
        self.stats['review_targets'] = float(self.stats.get('review_targets', 0.0) + float(len(review_targets)))
        node_ctx['_cx39_review_targets'] = [
            {'base_primitive_index': int(getattr(cand, 'primitive_index', -1)), 'prior_score': float(prior), 'review_score': float(review)}
            for cand, _, prior, review in review_targets
        ]
        extra_rows = list(extra or [])
        review_rows = detour_review_candidates(self.case, planner, h_pair, primitive_cands, review_targets)
        if review_rows:
            review_keys = search_state.setdefault('_cx39_review_keys', set())
            for cand in review_rows:
                try:
                    review_keys.add(planner._state_key(float(cand.next_state[0]), float(cand.next_state[1]), float(cand.next_state[2])))
                except Exception:
                    continue
            self.stats['review_candidates'] = float(self.stats.get('review_candidates', 0.0) + float(len(review_rows)))
        extra_rows.extend(review_rows)
        return extra_rows

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        base_ranked = self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        items = base_ranked if base_ranked is not None else [(cand, SuccessorDecision()) for cand in candidates]
        if self.disable_review_prior:
            return items
        ranked = []
        current_anchor, _ = h_pair(float(record.x), float(record.y), float(record.yaw))
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
            if str(getattr(cand, 'source', 'primitive')) == 'review':
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


def make_policy(memory: dict[str, Any], params: CX39ADRGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return DRGPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_detour_generator=bool(ablation.get('disable_detour_generator', False)),
        disable_review_prior=bool(ablation.get('disable_review_prior', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX39ADRGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
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
        {'haa_teacher': memory['haa_teacher'], 'typed_macro_families': memory['typed_macro_families'], 'typed_macro_support': memory['typed_macro_support'], 'event_contract': None},
    )


def build_standard_field(sample, predictor, params: CX39ADRGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
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
        {'haa_teacher': memory['haa_teacher'], 'typed_macro_families': memory['typed_macro_families'], 'typed_macro_support': memory['typed_macro_support'], 'event_contract': None},
    ).astype(np.float32)
