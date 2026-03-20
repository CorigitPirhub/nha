from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorDecision
from rs_cx.common import CXGlobalConfig
from rs_cx16.common import macro_successor_candidates
from rs_cx23.common import class_key
from rs_cx27.common import CX27WatchdogConfig
from rs_cx35 import cx35_b_tfmr as macro_parent
from rs_cx35.common import compile_typed_macro_support, reverse_pair_families
from rs_cx37 import cx37_a_rpt as replay_parent
from rs_cx38.common import bounded_local_review_score, replay_priority_prior, review_priority_delta


@dataclass(frozen=True)
class CX38ABLRParams:
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


def param_grid() -> list[CX38ABLRParams]:
    return [
        CX38ABLRParams(
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
        ),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Bounded-Review', 'disable_bounded_review': True},
        {'name': 'No-Replay-Activation', 'disable_replay_activation': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX38ABLRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = replay_parent.build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    typed = compile_typed_macro_support(
        calib_train_assets,
        teacher,
        families=reverse_pair_families(),
        min_hits=int(params.min_hits),
        out_dir=out_dir / 'typed_support',
    )
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
    replay_memory = replay_parent.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, replay_params, out_dir / 'replay_parent', device, {'haa_teacher': teacher})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx38_a_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'typed_families': {name: {'hits': int(stat.hits), 'avg_score': float(stat.avg_score)} for name, stat in typed['typed_macro_support'].items()} if 'typed_macro_support' in typed else {},
                'replay_contract': {
                    'positive_hits': int(replay_memory['replay_contract'].positive_hits),
                    'negative_hits': int(replay_memory['replay_contract'].negative_hits),
                    'margin_floor': float(replay_memory['replay_contract'].margin_floor),
                    'high_margin_floor': float(replay_memory['replay_contract'].high_margin_floor),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return {
        'haa_teacher': teacher,
        'typed_macro_families': replay_memory['typed_macro_families'],
        'typed_macro_support': replay_memory['typed_macro_support'],
        'replay_contract': replay_memory['replay_contract'],
        'best_val_loss': float('nan'),
    }


class BLRPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX38ABLRParams, memory: dict[str, Any], disable_bounded_review: bool = False, disable_replay_activation: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_bounded_review = bool(disable_bounded_review)
        self.disable_replay_activation = bool(disable_replay_activation)
        self.typed_macro_families = tuple(memory.get('typed_macro_families', reverse_pair_families()))
        self.typed_macro_support = dict(memory.get('typed_macro_support', {}))
        self.replay_contract = memory.get('replay_contract')
        self.watchdog_cfg = CX27WatchdogConfig(
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
        )
        self.base = macro_parent.make_policy(
            {'haa_teacher': memory['haa_teacher'], 'typed_macro_families': self.typed_macro_families, 'typed_macro_support': self.typed_macro_support},
            macro_parent.CX35BTFMRParams(
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
            ablation=None,
        )

    def start_search(self, planner, start, goal, h_pair, search_state):
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        search_state['last_record_x'] = float(record.x)
        search_state['last_record_y'] = float(record.y)
        search_state['last_record_yaw'] = float(record.yaw)
        ctx = self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict):
            ctx.pop('_cx38_review', None)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_replay_activation or not isinstance(node_ctx, dict):
            return extra
        active, macros, info = replay_priority_prior(
            self.case,
            self.bundle,
            node_ctx,
            search_state,
            record,
            h_pair,
            typed_families=self.typed_macro_families,
            typed_support=self.typed_macro_support,
            replay_contract=self.replay_contract,
            macro_spec=self.base.macro_spec,
            watchdog_cfg=self.watchdog_cfg,
        )
        if not active or not macros:
            return extra
        node_ctx['_cx38_review'] = dict(info)
        extra_rows = list(extra or [])
        extra_rows.extend(macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros)))
        return extra_rows

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        base_ranked = self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        items = base_ranked if base_ranked is not None else [(cand, SuccessorDecision()) for cand in candidates]
        if self.disable_bounded_review or not isinstance(node_ctx, dict):
            return items
        info = dict(node_ctx.get('_cx38_review', {}))
        if not info:
            return items
        current_anchor, _ = h_pair(float(record.x), float(record.y), float(record.yaw))
        prior_score = float(info.get('prior_score', 0.0))
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
            review = bounded_local_review_score(self.case, h_pair, float(current_anchor), cand)
            delta = review_priority_delta(float(review), float(prior_score))
            dec['priority_secondary_delta'] = float(dec.get('priority_secondary_delta', 0.0)) + float(delta)
            if getattr(cand, 'source', 'primitive') == 'macro':
                dec['priority_primary_delta'] = float(dec.get('priority_primary_delta', 0.0)) - 0.5 * float(delta)
            ranked.append((cand, dec))
        ranked.sort(key=lambda item: float(item[1].get('priority_secondary_delta', 0.0)))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.base, 'complete_expand'):
            return self.base.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX38ABLRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return BLRPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_bounded_review=bool(ablation.get('disable_bounded_review', False)),
        disable_replay_activation=bool(ablation.get('disable_replay_activation', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX38ABLRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return macro_parent.build_nonholonomic_field(
        case,
        predictor,
        cfg,
        macro_parent.CX35BTFMRParams(
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


def build_standard_field(sample, predictor, params: CX38ABLRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return macro_parent.build_standard_field(
        sample,
        predictor,
        macro_parent.CX35BTFMRParams(
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
