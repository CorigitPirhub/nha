from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx16.common import macro_successor_candidates
from rs_cx23.common import class_key
from rs_cx27.common import CX27WatchdogConfig
from rs_cx35 import cx35_b_tfmr as parent_mod
from rs_cx35.common import compile_typed_macro_support, reverse_pair_families
from rs_cx36.common import build_frozen_haa_stack, compile_event_trigger_contract, event_trigger_decision


@dataclass(frozen=True)
class CX36BETCParams:
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


def param_grid() -> list[CX36BETCParams]:
    return [
        CX36BETCParams(
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
        {'name': 'No-Event-Trigger', 'disable_event_trigger': True},
        {'name': 'No-Event-Contract', 'disable_event_contract': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX36BETCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    typed = compile_typed_macro_support(
        calib_train_assets,
        teacher,
        families=reverse_pair_families(),
        min_hits=int(params.min_hits),
        out_dir=out_dir / 'typed_support',
    )
    parent_params = parent_mod.CX35BTFMRParams(
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
    watchdog_cfg = CX27WatchdogConfig(
        cell_stride=int(params.cell_stride),
        yaw_bins=int(params.yaw_bins),
        progress_eps=float(params.progress_eps),
        commit_fail_margin=float(params.commit_fail_margin),
        failure_ttl=int(params.failure_ttl),
        history_window=int(params.history_window),
    )
    def _parent_factory(case, bundle, field):
        return parent_mod.make_policy(
            {'haa_teacher': teacher, 'typed_macro_families': typed['families'], 'typed_macro_support': typed['support']},
            parent_params,
            case,
            bundle,
            field,
            'cpu',
            ablation=None,
        )
    event_contract = compile_event_trigger_contract(
        calib_train_assets,
        _parent_factory,
        typed_families=typed['families'],
        typed_support=typed['support'],
        macro_spec=parent_mod.CX34SliceSpec(
            bridge_min=float(params.macro_bridge_min),
            bridge_max=float(params.macro_bridge_max),
            focus_min=float(params.macro_focus_min),
            focus_max=float(params.macro_focus_max),
            path_min=float(params.macro_path_min),
            path_max=float(params.macro_path_max),
        ),
        watchdog_cfg=watchdog_cfg,
        out_dir=out_dir / 'event_contract',
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx36_b_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'typed_families': {name: {'hits': int(stat.hits), 'avg_score': float(stat.avg_score)} for name, stat in typed['support'].items()},
                'event_contract': {
                    'positive_hits': int(event_contract.positive_hits),
                    'negative_hits': int(event_contract.negative_hits),
                    'margin_floor': float(event_contract.margin_floor),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return {
        'haa_teacher': teacher,
        'typed_macro_families': typed['families'],
        'typed_macro_support': typed['support'],
        'event_contract': event_contract,
        'best_val_loss': float('nan'),
    }


class ETCPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX36BETCParams, memory: dict[str, Any], disable_event_trigger: bool = False, disable_event_contract: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_event_trigger = bool(disable_event_trigger)
        self.disable_event_contract = bool(disable_event_contract)
        self.typed_macro_families = tuple(memory.get('typed_macro_families', reverse_pair_families()))
        self.typed_macro_support = dict(memory.get('typed_macro_support', {}))
        self.event_contract = memory.get('event_contract')
        self.watchdog_cfg = CX27WatchdogConfig(
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
        )
        self.base = parent_mod.make_policy(
            {'haa_teacher': memory['haa_teacher'], 'typed_macro_families': self.typed_macro_families, 'typed_macro_support': self.typed_macro_support},
            parent_mod.CX35BTFMRParams(
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
        return self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_event_trigger or not isinstance(node_ctx, dict):
            return extra
        allow, macros, _ = event_trigger_decision(
            self.case,
            self.bundle,
            node_ctx,
            search_state,
            record,
            h_pair,
            typed_families=self.typed_macro_families,
            typed_support=self.typed_macro_support,
            event_contract=self.event_contract,
            macro_spec=self.base.macro_spec,
            watchdog_cfg=self.watchdog_cfg,
        )
        if self.disable_event_contract and str(class_key(node_ctx)) == 'uncertain|none' and str(self.case.get('scenario', '')) != 'parasol_misc':
            allow = True
        if not allow or not macros:
            return extra
        extra_rows = list(extra or [])
        extra_rows.extend(macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros)))
        return extra_rows

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.base, 'complete_expand'):
            return self.base.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX36BETCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return ETCPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_event_trigger=bool(ablation.get('disable_event_trigger', False)),
        disable_event_contract=bool(ablation.get('disable_event_contract', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX36BETCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(
        case,
        predictor,
        cfg,
        parent_mod.CX35BTFMRParams(
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


def build_standard_field(sample, predictor, params: CX36BETCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(
        sample,
        predictor,
        parent_mod.CX35BTFMRParams(
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
